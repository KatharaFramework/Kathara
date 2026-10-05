import io
import json
import logging
import os
import re
import shutil
import tarfile
import tempfile
from typing import Any, Set, Dict, Generator, Tuple, List, Optional, Union

import docker
import docker.models.containers
import docker.models.networks
from docker.errors import DockerException, NotFound
from requests.exceptions import ConnectionError as RequestsConnectionError

from .DockerImage import DockerImage
from .DockerLink import DockerLink
from .DockerMachine import DockerMachine
from .DockerPlugin import DockerPlugin
from .exec_stream.DockerExecStream import DockerExecStream
from .stats.DockerLinkStats import DockerLinkStats
from .stats.DockerMachineStats import DockerMachineStats
from ... import utils
from ...decorators import privileged
from ...exceptions import DockerDaemonConnectionError, LinkNotFoundError, MachineCollisionDomainError, \
    InvocationError, LabNotFoundError, MachineNotRunningError
from ...exceptions import MachineNotFoundError
from ...foundation.manager.IManager import IManager
from ...model.Lab import Lab
from ...model.LabSerializer import lab_to_dict, lab_from_dict
from ...model.Link import Link
from ...model.Machine import Machine
from ...setting.Setting import Setting
from ...types import SharedCollisionDomainsOption
from ...utils import pack_files_for_tar, import_pywintypes, \
    check_required_single_not_none_var, check_single_not_none_var

pywintypes = import_pywintypes()


def check_docker_status(method):
    """Decorator function to check if Docker daemon is running properly."""

    @privileged
    def check_docker(*args, **kw):
        # Call the constructor first
        method(*args, **kw)

        # Client is initialized after constructor call
        client = args[0].client

        # Try to ping Docker, to see if it's running and raise an exception on failure
        try:
            client.ping()
        except RequestsConnectionError as e:
            raise DockerDaemonConnectionError(str(e))
        except pywintypes.error as e:
            raise DockerDaemonConnectionError(str(e))

    return check_docker


class DockerManager(IManager):
    """The class responsible to interact between Kathara and the Docker APIs."""
    __slots__ = ['client', 'docker_image', 'docker_machine', 'docker_link']

    # Paths excluded from filesystem-diff capture: Docker-managed files, pseudo-filesystems and
    # Kathara mount points. They are volatile or re-provided at deploy time, so they must not be saved.
    _DIFF_EXCLUDED_EXACT: frozenset = frozenset({
        "/etc/hosts", "/etc/hostname", "/etc/resolv.conf", "/etc/mtab", "/.dockerenv",
        "/hosthome", "/shared", "/hostlab",
    })
    _DIFF_EXCLUDED_PREFIXES: Tuple[str, ...] = (
        "/dev/", "/proc/", "/sys/", "/run/", "/tmp/", "/hosthome/", "/shared/", "/hostlab/",
    )

    @check_docker_status
    def __init__(self) -> None:
        remote_url = Setting.get_instance().remote_url
        try:
            if remote_url is None:
                self.client: docker.DockerClient = docker.from_env(timeout=None, max_pool_size=utils.get_pool_size())
            else:
                tls_config = docker.tls.TLSConfig(ca_cert=Setting.get_instance().cert_path)
                self.client: docker.DockerClient = docker.DockerClient(
                    base_url=remote_url, timeout=None, max_pool_size=utils.get_pool_size(), tls=tls_config
                )
        except DockerException as e:
            raise DockerDaemonConnectionError(str(e))

        docker_plugin = DockerPlugin(self.client)
        docker_plugin.check_and_download_plugin()

        self.docker_image: DockerImage = DockerImage(self.client)

        self.docker_machine: DockerMachine = DockerMachine(self.client, self.docker_image)
        self.docker_link: DockerLink = DockerLink(self.client, docker_plugin)

    @privileged
    def deploy_machine(self, machine: Machine) -> None:
        """Deploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            PrivilegeError: If the user start the device in privileged mode without having root privileges.
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        machine.check()

        self.docker_link.deploy_links(machine.lab, selected_links={x.link.name for x in machine.interfaces.values()})
        self.docker_machine.deploy_machines(machine.lab, selected_machines={machine.name})

    @privileged
    def deploy_link(self, link: Link) -> None:
        """Deploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        if not link.lab:
            raise LabNotFoundError("Collision domain `%s` is not associated to a network scenario." % link.name)

        self.docker_link.deploy_links(link.lab, selected_links={link.name})

    @privileged
    def deploy_lab(self, lab: Lab, selected_machines: Optional[Set[str]] = None,
                   excluded_machines: Optional[Set[str]] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Optional[Set[str]]): If not None, deploy only the specified devices.
            excluded_machines (Optional[Set[str]]): If not None, exclude devices from being deployed.

        Returns:
            None

        Raises:
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
            OSError: If any link in the network scenario is attached to external interfaces and the host OS is not LINUX.
            PrivilegeError: If the user start the network scenario in privileged mode without having root privileges.
            MachineNotFoundError: If the specified devices are not in the network scenario.
            InvocationError: If both `selected_machines` and `excluded_machines` are specified.
        """
        lab.check_integrity()

        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either select or exclude devices.")

        if selected_machines and not lab.has_machines(selected_machines):
            machines_not_in_lab = selected_machines - set(lab.machines.keys())
            raise MachineNotFoundError(f"The following devices are not in the network scenario: {machines_not_in_lab}.")

        if excluded_machines and not lab.has_machines(excluded_machines):
            machines_not_in_lab = excluded_machines - set(lab.machines.keys())
            raise MachineNotFoundError(f"The following devices are not in the network scenario: {machines_not_in_lab}.")

        selected_links = None
        if selected_machines:
            selected_links = lab.get_links_from_machines(selected_machines)

        excluded_links = None
        if excluded_machines:
            # Get the links of remaining machines
            running_links = lab.get_links_from_machines(set(lab.machines.keys()) - excluded_machines)
            # Get the links of the excluded machines and get the diff with the running ones
            # The remaining are the ones to delete
            excluded_links = lab.get_links_from_machines(excluded_machines) - running_links

        # Deploy all lab links.
        self.docker_link.deploy_links(lab, selected_links=selected_links, excluded_links=excluded_links)

        # Deploy all lab machines.
        self.docker_machine.deploy_machines(
            lab, selected_machines=selected_machines, excluded_machines=excluded_machines
        )

    @privileged
    def connect_machine_to_link(self, machine: Machine, link: Link, mac_address: Optional[str] = None,
                                vlan: Optional[int] = None, tagged_vlans: Optional[List[int]] = None) -> None:
        """Create a new interface on a running Kathara device and connect it to a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): A Kathara collision domain object.
            mac_address (Optional[str]): The MAC address to assign to the interface.
            vlan (Optional[int]): The VLAN of the untagged frames of the interface (managed collision domain).
            tagged_vlans (Optional[List[int]]): The VLANs exchanged tagged with the interface
                (managed collision domain).

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            MachineCollisionDomainConflictError: If the device is already connected to the collision domain.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        if not machine.api_object:
            raise MachineNotRunningError(machine.name)

        machine.api_object.reload()
        if machine.api_object.status != "running":
            raise MachineNotRunningError(machine.name)

        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        if machine.name in link.machines:
            raise MachineCollisionDomainError(
                f"Device `{machine.name}` is already connected to collision domain `{link.name}`."
            )

        iface_number = None
        if machine.is_bridged():
            if 'bridged_iface' not in machine.meta:
                machine.add_meta('bridged_iface', int(machine.api_object.labels['bridged_iface']))
            if not machine.interfaces or machine.meta['bridged_iface'] > max(machine.interfaces.keys()):
                iface_number = machine.meta['bridged_iface'] + 1
            else:
                iface_number = max(machine.interfaces.keys()) + 1

        interface = machine.add_interface(link, mac_address=mac_address, number=iface_number,
                                          vlan=vlan, tagged_vlans=tagged_vlans)

        self.deploy_link(link)
        self.docker_machine.connect_interface(machine, interface)

    @privileged
    def disconnect_machine_from_link(self, machine: Machine, link: Link, keep_link: bool = False) -> None:
        """Disconnect a running Kathara device from a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): The Kathara collision domain from which disconnect the running device.
            keep_link (bool): Keep collision domain. Default: False.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            MachineCollisionDomainConflictError: If the device is not connected to the collision domain.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        if not machine.api_object:
            raise MachineNotRunningError(machine.name)

        machine.api_object.reload()
        if machine.api_object.status != "running":
            raise MachineNotRunningError(machine.name)

        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        if machine.name not in link.machines:
            raise MachineCollisionDomainError(
                f"Device `{machine.name}` is not connected to collision domain `{link.name}`."
            )

        machine.remove_interface(link)

        self.docker_machine.disconnect_from_link(machine, link)
        if not keep_link:
            self.undeploy_link(link)

    @privileged
    def undeploy_machine(self, machine: Machine, keep_links: bool = False) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            keep_links (bool): Keep device's collision domains when undeploying. Default: False.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        self.docker_machine.undeploy(machine.lab.hash, selected_machines={machine.name})
        if not keep_links:
            self.docker_link.undeploy(
                machine.lab.hash, selected_links={x.link.name for x in machine.interfaces.values()}
            )

    @privileged
    def undeploy_link(self, link: Link) -> None:
        """Undeploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        self.docker_link.undeploy(link.lab.hash, selected_links={link.name})

    @privileged
    def undeploy_lab(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                     selected_machines: Optional[Set[str]] = None,
                     excluded_machines: Optional[Set[str]] = None,
                     selected_links: Optional[Set[str]] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            selected_machines (Optional[Set[str]]): If not None, undeploy only the specified devices.
            excluded_machines (Optional[Set[str]]): If not None, exclude devices from being undeployed.
            selected_links (Optional[Set[str]]): If not None, undeploy only the specified collision domains.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash or name is not specified,
                or if both `selected_machines` and `excluded_machines` are specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either select or exclude devices.")

        self.docker_machine.undeploy(lab_hash, selected_machines=selected_machines, excluded_machines=excluded_machines)

        self.docker_link.undeploy(lab_hash, selected_links=selected_links)

    @privileged
    def save_lab(self, archive_path: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                 lab: Optional[Lab] = None, selected_machines: Optional[Set[str]] = None,
                 excluded_machines: Optional[Set[str]] = None, filesystem_diff: bool = True) -> None:
        """Save the state of a running network scenario into a single archive file.

        In the default `filesystem_diff` mode, only the filesystem changes of each device relative to
        its base image are saved (smaller archive, but the base image must be available on restore).
        When `filesystem_diff` is False, each running device is committed into a full local image and
        the whole images are bundled (larger archive, but fully self-contained). The scenario can later
        be recreated with `restore_lab`.

        Args:
            archive_path (str): The path of the archive file to create.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            selected_machines (Optional[Set[str]]): If not None, save only the specified devices.
            excluded_machines (Optional[Set[str]]): If not None, exclude devices from being saved.
            filesystem_diff (bool): If True (default), save only the filesystem diff of each device
                relative to its base image. If False, save the full committed device images.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash, name or object is not specified,
                or if both `selected_machines` and `excluded_machines` are specified.
            MachineNotFoundError: If there are no devices to save in the network scenario.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if selected_machines and excluded_machines:
            raise InvocationError("You can either select or exclude devices.")

        # Refresh the topology (and device api_objects) from the running backend.
        if lab is None:
            lab = self.get_lab_from_api(lab_hash=lab_hash, lab_name=lab_name)
        else:
            self.update_lab_from_api(lab)

        machine_names = set(lab.machines.keys())
        if selected_machines:
            machine_names &= selected_machines
        if excluded_machines:
            machine_names -= excluded_machines

        if not machine_names:
            raise MachineNotFoundError("There are no devices to save in the network scenario.")

        # Docker repository names must be lowercase alphanumeric; sanitize the lab hash.
        safe_hash = re.sub(r"[^a-z0-9]", "", lab.hash.lower())
        committed_images: Dict[str, str] = {}     # device -> full committed image ref (full mode)
        diff_files: Dict[str, str] = {}           # device -> temp diff tarball path (diff mode)
        original_images: Dict[str, str] = {}      # device -> base image
        deletions: Dict[str, List[str]] = {}      # device -> deleted paths (diff mode)

        try:
            for name in sorted(machine_names):
                machine = lab.machines[name]
                if machine.api_object is None:
                    logging.warning(f"Device `{name}` is not running, its runtime state will not be saved.")
                    continue

                machine.api_object.reload()
                original_images[name] = machine.get_image()

                if filesystem_diff:
                    logging.info(f"Computing filesystem diff of device `{name}`...")
                    diff_files[name], deletions[name] = self._build_device_diff(machine.api_object)
                else:
                    image_ref = self.docker_image.commit_container(
                        machine.api_object, repository=f"kathara_save_{safe_hash}", tag=name
                    )
                    committed_images[name] = image_ref

                # Point the device at the image that restore will provide (committed or reconstructed).
                machine.meta["image"] = f"kathara_save_{safe_hash}:{name}"

            manifest = lab_to_dict(lab)
            manifest["save_mode"] = "diff" if filesystem_diff else "full"
            # Keep only the saved devices in the manifest and annotate base images and deletions.
            manifest["machines"] = [
                {**machine_dict,
                 "original_image": original_images.get(machine_dict["name"]),
                 "deletions": deletions.get(machine_dict["name"], [])}
                for machine_dict in manifest["machines"] if machine_dict["name"] in machine_names
            ]
            # Keep only the collision domains referenced by the saved devices.
            saved_links = {
                iface["link"] for machine_dict in manifest["machines"] for iface in machine_dict["interfaces"]
            }
            manifest["links"] = [link for link in manifest["links"] if link["name"] in saved_links]

            self._write_save_archive(archive_path, lab, manifest, committed_images, diff_files)
        finally:
            # The archive is now the source of truth; drop intermediate committed images and temp diffs.
            for image_ref in committed_images.values():
                self.docker_image.remove_image(image_ref)
            for diff_path in diff_files.values():
                if os.path.exists(diff_path):
                    os.remove(diff_path)

    def _build_device_diff(self, container: docker.models.containers.Container) -> Tuple[str, List[str]]:
        """Build the filesystem diff of a running container relative to its base image.

        Captures added/modified files (excluding Docker-managed and Kathara-mount paths) into a
        temporary tarball with absolute member paths, and returns the list of deleted paths.

        Args:
            container (docker.models.containers.Container): The container to diff.

        Returns:
            Tuple[str, List[str]]: The path of the temporary diff tarball and the list of deleted paths.
        """
        changes = container.diff() or []
        all_paths = {change["Path"] for change in changes}

        # Kind: 0 = Modified, 1 = Added, 2 = Deleted.
        deleted = sorted(
            change["Path"] for change in changes
            if change["Kind"] == 2 and not self._is_diff_path_excluded(change["Path"])
        )

        # A changed path is a "leaf" when no other changed path lives underneath it. Capturing only
        # leaves avoids pulling the whole contents of a directory that is merely marked as modified.
        def is_leaf(path: str) -> bool:
            prefix = path + "/"
            return not any(other != path and other.startswith(prefix) for other in all_paths)

        leaves = [
            change["Path"] for change in changes
            if change["Kind"] in (0, 1)
            and not self._is_diff_path_excluded(change["Path"])
            and is_leaf(change["Path"])
        ]

        diff_fd, diff_path = tempfile.mkstemp(prefix="kathara_diff_", suffix=".tar")
        with os.fdopen(diff_fd, "wb") as diff_file:
            with tarfile.open(fileobj=diff_file, mode="w") as diff_tar:
                for path in leaves:
                    try:
                        bits, _ = container.get_archive(path)
                    except NotFound:
                        continue

                    parent = os.path.dirname(path).lstrip("/")
                    with tarfile.open(fileobj=io.BytesIO(b"".join(bits))) as src_tar:
                        for member in src_tar.getmembers():
                            # Keep only the top-level entry (the path itself), not directory contents.
                            if "/" in member.name:
                                continue
                            member.name = "/".join(filter(None, [parent, member.name]))
                            if member.isfile():
                                diff_tar.addfile(member, src_tar.extractfile(member))
                            else:
                                diff_tar.addfile(member)

        return diff_path, deleted

    @classmethod
    def _is_diff_path_excluded(cls, path: str) -> bool:
        """Return True if the path must be excluded from a filesystem-diff capture."""
        return path in cls._DIFF_EXCLUDED_EXACT or path.startswith(cls._DIFF_EXCLUDED_PREFIXES)

    @privileged
    def restore_lab(self, archive_path: str, lab_hash: Optional[str] = None,
                    lab: Optional[Lab] = None) -> Lab:
        """Restore a network scenario previously saved with `save_lab` and redeploy it.

        For a full-image save, the bundled images are loaded into the local Docker repository. For a
        filesystem-diff save, each device image is reconstructed from its base image plus the saved
        diff. The topology is then rebuilt from the manifest (or taken from `lab`) and the scenario
        is deployed.

        Args:
            archive_path (str): The path of the archive file created by `save_lab`.
            lab_hash (Optional[str]): If specified, override the hash of the restored network scenario.
            lab (Optional[Kathara.model.Lab]): If specified, deploy this network scenario instead of the
                one rebuilt from the manifest: each of its devices that appears in the save file is pointed
                at the restored image, every other device option and the topology come from `lab`, the
                saved scenario files are uploaded into `lab.fs`, and `lab_hash` is ignored.

        Returns:
            Kathara.model.Lab: The restored (and redeployed) network scenario.

        Raises:
            InvocationError: If the archive is not a valid Kathara save file.
        """
        with tarfile.open(archive_path, "r") as tar:
            manifest_member = tar.extractfile("manifest.json") if "manifest.json" in tar.getnames() else None
            if manifest_member is None:
                raise InvocationError(f"Invalid Kathara save file `{archive_path}`: missing `manifest.json`.")
            manifest = json.loads(manifest_member.read().decode("utf-8"))

            if manifest.get("save_mode") == "diff":
                self._restore_diff_images(tar, manifest)
            else:
                # Load the full committed images. The extracted member is streamed so large images
                # are not read fully into memory.
                for member in tar.getmembers():
                    if member.isfile() and member.name.startswith("images/"):
                        logging.info(f"Loading saved image `{member.name}`... This may take a while.")
                        self.docker_image.load_images_from_tar(tar.extractfile(member))

            if lab is None:
                lab = lab_from_dict(manifest)
                if lab_hash:
                    lab.hash = lab_hash
            else:
                # The caller provides the topology and device options; only the images come from the save file.
                self._apply_saved_images(lab, manifest)

            # Restore the network scenario files (startup/shutdown/shared/device dirs) into the lab filesystem.
            for member in tar.getmembers():
                if member.isfile() and member.name.startswith("lab/"):
                    dst_path = member.name[len("lab"):]  # keep the leading slash for the fs
                    parent = os.path.dirname(dst_path)
                    if parent and parent != "/":
                        lab.fs.makedirs(parent, recreate=True)
                    with tar.extractfile(member) as src:
                        lab.fs.upload(dst_path, src)

        self.deploy_lab(lab)

        return lab

    @staticmethod
    def _apply_saved_images(lab: Lab, manifest: Dict) -> None:
        """Point the devices of `lab` that are in the save file at the restored images."""
        saved_images = {machine_dict["name"]: machine_dict["meta"]["image"] for machine_dict in manifest["machines"]}

        for name, machine in lab.machines.items():
            if name in saved_images:
                machine.add_meta("image", saved_images[name])
            else:
                logging.warning(f"Device `{name}` is not in the save file: it will be deployed from its own image.")

        for name in sorted(saved_images.keys() - lab.machines.keys()):
            logging.warning(f"Saved device `{name}` is not in the network scenario: its saved state is ignored.")

    def _restore_diff_images(self, tar: tarfile.TarFile, manifest: Dict) -> None:
        """Reconstruct each device image from its base image and saved filesystem diff."""
        machines_by_name = {machine_dict["name"]: machine_dict for machine_dict in manifest["machines"]}

        for member in tar.getmembers():
            if not (member.isfile() and member.name.startswith("images/") and member.name.endswith(".diff.tar")):
                continue

            name = os.path.basename(member.name)[:-len(".diff.tar")]
            machine_dict = machines_by_name.get(name)
            if machine_dict is None:
                continue

            base_image = machine_dict["original_image"]
            target_ref = machine_dict["meta"]["image"]
            deletions = machine_dict.get("deletions", [])

            # Ensure the base image is available before reconstructing on top of it.
            self.docker_image.check_from_list({base_image})

            logging.info(f"Reconstructing image of device `{name}` from base `{base_image}`...")
            diff_fd, diff_path = tempfile.mkstemp(prefix="kathara_diff_", suffix=".tar")
            try:
                with os.fdopen(diff_fd, "wb") as diff_file:
                    shutil.copyfileobj(tar.extractfile(member), diff_file)
                self.docker_image.build_image_from_diff(base_image, target_ref, diff_path, deletions)
            finally:
                os.remove(diff_path)

    def _write_save_archive(self, archive_path: str, lab: Lab, manifest: Dict,
                            committed_images: Dict[str, str], diff_files: Dict[str, str]) -> None:
        """Write the save archive: manifest.json, device images (full or diff), and lab filesystem files.

        Full images are streamed to disk (via a temporary file) before being added to the archive, so
        that large images are never fully loaded into memory. Diff tarballs are added directly.
        """
        archive_abspath = os.path.abspath(archive_path)

        with tarfile.open(archive_path, "w") as tar:
            self._add_bytes_to_tar(tar, "manifest.json", json.dumps(manifest, indent=2).encode("utf-8"))

            for name, image_ref in committed_images.items():
                logging.info(f"Exporting saved image of device `{name}`... This may take a while.")
                tmp_fd, tmp_path = tempfile.mkstemp(prefix="kathara_save_", suffix=".tar")
                try:
                    with os.fdopen(tmp_fd, "wb") as tmp_file:
                        for chunk in self.docker_image.save_image_to_tar(image_ref):
                            tmp_file.write(chunk)
                    tar.add(tmp_path, arcname=f"images/{name}.tar")
                finally:
                    os.remove(tmp_path)

            for name, diff_path in diff_files.items():
                tar.add(diff_path, arcname=f"images/{name}.diff.tar")

            for path in lab.fs.walk.files():
                # Skip the output archive itself, in case it is being written inside the lab directory.
                if lab.fs.hassyspath(path) and os.path.abspath(lab.fs.getsyspath(path)) == archive_abspath:
                    continue
                self._add_bytes_to_tar(tar, f"lab{path}", lab.fs.readbytes(path))

    @staticmethod
    def _add_bytes_to_tar(tar: tarfile.TarFile, name: str, data: bytes) -> None:
        """Add an in-memory bytes payload as a file entry inside an open tar archive."""
        tar_info = tarfile.TarInfo(name=name)
        tar_info.size = len(data)
        tar.addfile(tar_info, io.BytesIO(data))

    @privileged
    def wipe(self, all_users: bool = False) -> None:
        """Undeploy all the running network scenarios.

        If multiuser scenarios are active, undeploy only current user devices.

        Args:
            all_users (bool): If false, undeploy only the current user network scenarios. If true, undeploy the
                running network scenarios of all users.

        Returns:
            None
        """
        if Setting.get_instance().remote_url is not None and all_users:
            all_users = False
            logging.warning("Cannot wipe devices of other users with a remote Docker connection.")

        user_name = utils.get_current_user_name() if not all_users else None

        self.docker_machine.wipe(user=user_name)
        self.docker_link.wipe(user=user_name)

    @privileged
    def connect_tty(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                    lab: Optional[Lab] = None, shell: str = None, logs: bool = False,
                    wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine_name (str): The name of the device to connect.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before connecting. If a tuple is provided, the first value indicates the number of retries
                before stopping waiting and the second value indicates the time interval to wait for each retry.
                Default is True.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name()

        self.docker_machine.connect(lab_hash=lab_hash,
                                    machine_name=machine_name,
                                    user=user_name,
                                    shell=shell,
                                    logs=logs,
                                    wait=wait
                                    )

    def connect_tty_obj(self, machine: Machine, shell: str = None, logs: bool = False,
                        wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine (Machine): The device to connect.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before connecting. If a tuple is provided, the first value indicates the number of retries
                before stopping waiting and the second value indicates the time interval to wait for each retry.
                Default is True.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        self.connect_tty(machine.name, lab=machine.lab, shell=shell, logs=logs, wait=wait)

    @privileged
    def exec(self, machine_name: str, command: Union[List[str], str], lab_hash: Optional[str] = None,
             lab_name: Optional[str] = None, lab: Optional[Lab] = None, wait: Union[bool, Tuple[int, float]] = False,
             stream: bool = True) -> Union[DockerExecStream, Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine_name (str): The name of the device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return a DockerExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[DockerExecStream, Tuple[bytes, bytes, int]]: A DockerExecStream object or
            a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotRunningError: If the specified device is not running.
            ValueError: If the wait values is neither a boolean nor a tuple, or an invalid tuple.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name()
        return self.docker_machine.exec(
            lab_hash, machine_name, command, user=user_name, tty=False, wait=wait, stream=stream
        )

    def exec_obj(self, machine: Machine, command: Union[List[str], str], wait: Union[bool, Tuple[int, float]] = False,
                 stream: bool = True) -> Union[DockerExecStream, Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine (Machine): The device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return a DockerExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[DockerExecStream, Tuple[bytes, bytes, int]]: A DockerExecStream object or
            a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the binary of the command is not found.
            ValueError: If the wait values is neither a boolean nor a tuple, or an invalid tuple.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        return self.exec(machine.name, command, lab=machine.lab, wait=wait, stream=stream)

    @privileged
    def exec_link(self, link_name: str, command: str, lab_hash: Optional[str] = None,
                  lab_name: Optional[str] = None, lab: Optional[Lab] = None) -> str:
        """Run a command on the management console of a managed collision domain in a running network scenario.

        Args:
            link_name (str): The name of the collision domain.
            command (str): The command, e.g. `vlan/create 10` or `port/print`.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.

        Returns:
            str: The text printed by the command.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            LinkNotFoundError: If the collision domain is not found.
            LinkModeError: If the collision domain is not a managed switch.
            LinkCommandError: If the command fails.
            NotSupportedError: If the manager cannot manage collision domains.
        """
        return self.docker_link.exec(self.get_link_api_object(link_name, lab_hash, lab_name, lab), command)

    def exec_link_obj(self, link: Link, command: str) -> str:
        """Run a command on the management console of a managed collision domain in a running network scenario.

        Args:
            link (Kathara.model.Link): The collision domain.
            command (str): The command, e.g. `vlan/create 10` or `port/print`.

        Returns:
            str: The text printed by the command.

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            LinkNotFoundError: If the collision domain is not found.
            LinkModeError: If the collision domain is not a managed switch.
            LinkCommandError: If the command fails.
            NotSupportedError: If the manager cannot manage collision domains.
        """
        if not link.lab:
            raise LabNotFoundError(f"Link `{link.name}` is not associated to a network scenario.")

        return self.exec_link(link.name, command, lab=link.lab)

    @privileged
    def get_link_ports(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                       lab: Optional[Lab] = None) -> Dict[int, Dict[str, Any]]:
        """Return the ports of a managed collision domain in a running network scenario.

        Args:
            link_name (str): The name of the collision domain.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.

        Returns:
            Dict[int, Dict[str, Any]]: For each port number: `vlan` (the VLAN of the untagged frames),
                `tagged_vlans` (the VLANs exchanged tagged), `active` (True when something is plugged) and
                `endpoints` (what is plugged: `<device>:eth<N>` for the interface of a device).

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            LinkNotFoundError: If the collision domain is not found.
            LinkModeError: If the collision domain is not a managed switch.
            NotSupportedError: If the manager cannot manage collision domains.
        """
        return self.docker_link.get_ports(self.get_link_api_object(link_name, lab_hash, lab_name, lab))

    def get_link_ports_obj(self, link: Link) -> Dict[int, Dict[str, Any]]:
        """Return the ports of a managed collision domain in a running network scenario.

        Args:
            link (Kathara.model.Link): The collision domain.

        Returns:
            Dict[int, Dict[str, Any]]: For each port number: `vlan` (the VLAN of the untagged frames),
                `tagged_vlans` (the VLANs exchanged tagged), `active` (True when something is plugged) and
                `endpoints` (what is plugged: `<device>:eth<N>` for the interface of a device).

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            LinkNotFoundError: If the collision domain is not found.
            LinkModeError: If the collision domain is not a managed switch.
            NotSupportedError: If the manager cannot manage collision domains.
        """
        if not link.lab:
            raise LabNotFoundError(f"Link `{link.name}` is not associated to a network scenario.")

        return self.get_link_ports(link.name, lab=link.lab)

    @privileged
    def copy_files(self, machine: Machine, guest_to_host: Dict[str, Union[str, io.IOBase]]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            guest_to_host (Dict[str, Union[str, io.IOBase]]): A dict containing the device path as key and a
                fileobj to copy in path as value or a path to a file.

        Returns:
            None
        """
        tar_data = pack_files_for_tar(guest_to_host)

        self.docker_machine.copy_files(machine.api_object,
                                       path="/",
                                       tar_data=tar_data
                                       )

    @privileged
    def retrieve_files(self, machine: Machine, src: str, dst: str) -> None:
        """Copy files from a running device path to the host.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            src (str): The path of the file or folder to copy from the device.
            dst (str): The destination path on the host.

        Returns:
            None
        """
        self.docker_machine.retrieve_files(machine.api_object, src, dst)

    @privileged
    def get_machine_api_object(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                               lab: Optional[Lab] = None, all_users: bool = False) \
            -> docker.models.containers.Container:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            machine_name (str): The name of the device.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            docker.models.containers.Container: Docker API object of devices.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotFoundError: If the specified device is not found.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        containers = self.docker_machine.get_machines_api_objects_by_filters(
            lab_hash=lab_hash, machine_name=machine_name, user=user_name
        )
        if containers:
            return containers.pop()

        raise MachineNotFoundError(f"Device `{machine_name}` not found.")

    @privileged
    def get_machines_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                                 lab: Optional[Lab] = None, all_users: bool = False) \
            -> List[docker.models.containers.Container]:
        """Return API objects of running devices.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            List[docker.models.containers.Container]: Docker API objects of devices.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

    @privileged
    def get_link_api_object(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                            lab: Optional[Lab] = None, all_users: bool = False) -> docker.models.networks.Network:
        """Return the corresponding API object of a collision domain in a network scenario.

        Args:
            link_name (str): The name of the collision domain.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            docker.models.networks.Network: Docker API object of the network.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            LinkNotFoundError: If the collision domain is not found.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        networks = self.docker_link.get_links_api_objects_by_filters(
            lab_hash=lab_hash, link_name=link_name, user=user_name
        )
        if networks:
            return networks.pop()

        raise LinkNotFoundError(f"Collision Domain `{link_name}` not found.")

    @privileged
    def get_links_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                              lab: Optional[Lab] = None, all_users: bool = False) \
            -> List[docker.models.networks.Network]:
        """Return API objects of collision domains in a network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            List[docker.models.networks.Network]: Docker API objects of networks.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_link.get_links_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

    @privileged
    def get_lab_from_api(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None) -> Lab:
        """Return the network scenario (specified by the hash or name), building it from API objects.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name. If None, lab_name should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash. If None, lab_hash should be set.

        Returns:
            Lab: The built network scenario.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        if not lab_hash and not lab_name:
            raise InvocationError("You must specify a running network scenario hash or name.")

        if lab_name:
            reconstructed_lab = Lab(lab_name)
        else:
            reconstructed_lab = Lab("reconstructed_lab")
            reconstructed_lab.hash = lab_hash

        lab_containers = self.get_machines_api_objects(lab_hash=reconstructed_lab.hash)
        lab_networks = dict(
            map(lambda x: (x.name, x), self.get_links_api_objects(
                lab_hash=reconstructed_lab.hash \
                    if Setting.get_instance().shared_cds == SharedCollisionDomainsOption.NOT_SHARED else None,
                all_users=Setting.get_instance().shared_cds == SharedCollisionDomainsOption.USERS
            ))
        )

        for container in lab_containers:
            container.reload()
            device = reconstructed_lab.get_or_new_machine(container.labels["name"])
            device.api_object = container

            # Rebuild device metas
            # NOTE: We cannot rebuild "exec", "ipv6" and "num_terms" meta.
            device.add_meta("privileged", container.attrs["HostConfig"]["Privileged"])
            device.add_meta("image", container.attrs["Config"]["Image"])
            device.add_meta("shell", container.attrs["Config"]["Labels"]["shell"])

            # Memory is always returned in MBytes
            if container.attrs['HostConfig']['Memory'] > 0:
                device.add_meta("mem", f"{int(container.attrs['HostConfig']['Memory'] / (1024 ** 2))}M")

            # Reconvert nanocpus to a value passed by the user
            if container.attrs["HostConfig"]["NanoCpus"] > 0:
                device.add_meta("cpu", container.attrs["HostConfig"]["NanoCpus"] / 1000000000)

            for env in container.attrs["Config"]["Env"]:
                device.add_meta("env", env)

            # Reconvert ports to the device format
            if container.attrs['HostConfig']['PortBindings']:
                for port_info, port_data in container.attrs['HostConfig']['PortBindings'].items():
                    (guest_port, protocol) = port_info.split('/')
                    host_port = port_data[0]["HostPort"]
                    device.meta["ports"][(int(host_port), protocol)] = int(guest_port)

            # Reassign sysctls directly
            device.meta["sysctls"] = container.attrs["HostConfig"]["Sysctls"]

            if "none" not in container.attrs["NetworkSettings"]["Networks"]:
                if "bridge" in container.attrs["NetworkSettings"]["Networks"].keys():
                    device.add_meta("bridged", True)
                    device.add_meta("bridged_iface", int(container.labels['bridged_iface']))
                    container.attrs["NetworkSettings"]["Networks"].pop("bridge")

                networks = sorted(container.attrs["NetworkSettings"]["Networks"].items(),
                                  key=lambda x: x[1]["DriverOpts"]["kathara.iface"])

                for network_name, network_options in networks:
                    network = lab_networks[network_name]
                    link = reconstructed_lab.get_or_new_link(network.attrs["Labels"]["name"])
                    link.api_object = network
                    link.mode = self.docker_link.get_link_mode(network)
                    iface_number = int(network_options["DriverOpts"]["kathara.iface"])

                    iface_mac_addr = None
                    if network_options["DriverOpts"] is not None:
                        if "kathara.mac_addr" in network_options["DriverOpts"]:
                            iface_mac_addr = network_options["DriverOpts"]["kathara.mac_addr"]
                        if "com.docker.network.endpoint.sysctls" in network_options["DriverOpts"]:
                            for s in network_options["DriverOpts"]["com.docker.network.endpoint.sysctls"].split(","):
                                device.add_meta("sysctl", s.replace("IFNAME", f"eth{iface_number}"))

                    device.add_interface(link, mac_address=iface_mac_addr, number=iface_number,
                                         **self.docker_machine.get_interface_vlans(network_options["DriverOpts"]))

        return reconstructed_lab

    @privileged
    def update_lab_from_api(self, lab: Lab) -> None:
        """Update the passed network scenario from API objects.

        Args:
            lab (Lab): The network scenario to update.
        """
        running_containers = self.get_machines_api_objects(lab_hash=lab.hash)

        deployed_networks = dict(
            map(lambda x: (x.name, x), self.get_links_api_objects(
                lab_hash=lab.hash \
                    if Setting.get_instance().shared_cds == SharedCollisionDomainsOption.NOT_SHARED else None,
                all_users=Setting.get_instance().shared_cds == SharedCollisionDomainsOption.USERS
            ))
        )
        for network in deployed_networks.values():
            network.reload()

        deployed_networks_by_link_name = dict(
            map(lambda x: (x.attrs["Labels"]["name"], x), deployed_networks.values())
        )

        for container in running_containers:
            container.reload()
            device = lab.get_or_new_machine(container.labels["name"])
            device.api_object = container

            # Collision domains declared in the network scenario
            static_links = set([x.link for x in device.interfaces.values()])
            # Interfaces currently attached to the device
            if "bridge" in container.attrs["NetworkSettings"]["Networks"].keys():
                container.attrs["NetworkSettings"]["Networks"].pop("bridge")

            if "none" in container.attrs["NetworkSettings"]["Networks"].keys():
                container.attrs["NetworkSettings"]["Networks"].pop("none")

            current_ifaces = [
                (lab.get_or_new_link(deployed_networks[name].attrs["Labels"]["name"]), options)
                for name, options in sorted(container.attrs["NetworkSettings"]["Networks"].items(),
                                            key=lambda x: x[1]["DriverOpts"]["kathara.iface"])
            ]

            # Collision domains currently attached to the device
            current_links = set(map(lambda x: x[0], current_ifaces))
            # Collision domains attached at runtime to the device
            dynamic_links = current_links - static_links
            # Static collision domains detached at runtime from the device
            deleted_links = static_links - current_links

            for link in static_links:
                if link.name in deployed_networks_by_link_name:
                    link.api_object = deployed_networks_by_link_name[link.name]
                    if link.mode is None:
                        link.mode = self.docker_link.get_link_mode(link.api_object)

            current_ifaces = dict([(x[0].name, x[1]) for x in current_ifaces])
            for link in dynamic_links:
                link.api_object = deployed_networks_by_link_name[link.name]
                link.mode = self.docker_link.get_link_mode(link.api_object)
                iface_options = current_ifaces[link.name]
                iface_mac_addr = None
                iface_number = int(iface_options["DriverOpts"]["kathara.iface"])

                if iface_options["DriverOpts"] is not None:
                    if "kathara.mac_addr" in iface_options["DriverOpts"]:
                        iface_mac_addr = iface_options["DriverOpts"]["kathara.mac_addr"]
                    if "com.docker.network.endpoint.sysctls" in iface_options["DriverOpts"]:
                        for s in iface_options["DriverOpts"]["com.docker.network.endpoint.sysctls"].split(","):
                            device.add_meta("sysctl", s.replace("IFNAME", f"eth{iface_number}"))

                device.add_interface(link, mac_address=iface_mac_addr, number=iface_number,
                                     **self.docker_machine.get_interface_vlans(iface_options["DriverOpts"]))

            for link in deleted_links:
                device.remove_interface(link)

    @privileged
    def get_machines_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                           lab: Optional[Lab] = None, machine_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, DockerMachineStats], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            machine_name (str): If specified return all the devices with machine_name.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, DockerMachineStats], None, None]: A generator containing dicts that has API Object
              identifier as keys and DockerMachineStats objects as values.

        Raises:
            InvocationError: If more than one param among lab_hash, lab_name and lab is specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)

        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_machine.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name,
                                                      user=user_name)

    @privileged
    def get_machine_stats(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                          lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[DockerMachineStats], None, None]:
        """Return information of the specified device in a specified network scenario.

         Args:
            machine_name (str): The name of the device for which statistics are requested.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            Generator[Optional[DockerMachineStats], None, None]: A generator containing the DockerMachineStats object
            with the device info. Returns None if the device is not found.

        Raises:
            InvocationError: If a running network scenario hash, name or object is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)

        machines_stats = self.get_machines_stats(lab_hash=lab_hash, lab_name=lab_name, lab=lab,
                                                 machine_name=machine_name, all_users=all_users)
        machines_stats_next = next(machines_stats)
        if machines_stats_next:
            (_, machine_stats) = machines_stats_next.popitem()
            yield machine_stats
        else:
            yield None

    def get_machine_stats_obj(self, machine: Machine, all_users: bool = False) \
            -> Generator[Optional[DockerMachineStats], None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine (Machine): The device for which statistics are requested.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            Generator[Optional[IMachineStats], None, None]: A generator containing the IMachineStats object
            with the device info. Returns None if the device is not found.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        return self.get_machine_stats(machine.name, lab=machine.lab, all_users=all_users)

    @privileged
    def get_links_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                        link_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, DockerLinkStats], None, None]:
        """Return information about deployed networks.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
           link_name (str): If specified return all the networks with link_name.
           all_users (bool): If True, return information about the networks of all users.

        Returns:
             Generator[Dict[str, DockerLinkStats], None, None]: A generator containing dicts that has API Object
                identifier as keys and DockerLinksStats objects as values.

        Raises:
            InvocationError: If a running network scenario hash, name or object is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_link.get_links_stats(lab_hash=lab_hash, link_name=link_name, user=user_name)

    @privileged
    def get_link_stats(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                       lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[DockerLinkStats], None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link_name (str): The name of the collision domain for which statistics are requested.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about the networks of all users.

        Returns:
            Generator[Optional[DockerLinkStats], None, None]: A generator containing the DockerLinkStats object
            with the network info. Returns None if the network is not found.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        links_stats = self.get_links_stats(lab_hash=lab_hash, link_name=link_name, all_users=all_users)
        links_stats_next = next(links_stats)
        if links_stats_next:
            (_, link_stats) = links_stats_next.popitem()
            yield link_stats
        else:
            yield None

    def get_link_stats_obj(self, link: Link, all_users: bool = False) \
            -> Generator[Optional[DockerLinkStats], None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link (Link): The collision domain for which statistics are requested.
            all_users (bool): If True, return information about the networks of all users.

        Returns:
            Generator[Optional[ILinkStats], None, None]: A generator containing the ILinkStats object
            with the network info. Returns None if the network is not found.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        if not link.lab:
            raise LabNotFoundError(f"Link `{link.name}` is not associated to a network scenario.")

        return self.get_link_stats(link.name, lab=link.lab, all_users=all_users)

    @privileged
    def check_image(self, image_name: str) -> None:
        """Check if the specified image is valid.

        Args:
            image_name (str): The name of the image

        Returns:
            None

        Raises:
            ConnectionError: If the image is not locally available and there is no connection to a remote image repository.
            DockerImageNotFoundError: If the image is not found.
        """
        self.docker_image.check(image_name)

    @privileged
    def get_release_version(self) -> str:
        """Return the current manager version.

        Returns:
            str: The current manager version.
        """
        return self.client.version()["Version"]

    @staticmethod
    def get_formatted_manager_name() -> str:
        """Return a formatted string containing the current manager name.

        Returns:
            str: A formatted string containing the current manager name.
        """
        return "Docker (Kathara)"
