import sys
from unittest import mock
from unittest.mock import Mock, call

import docker.types
import pytest

sys.path.insert(0, './')

from src.Kathara.model.ExternalLink import ExternalLink
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Link import BRIDGE_LINK_NAME
from src.Kathara.manager.docker.DockerLink import DockerLink
from src.Kathara import utils
from src.Kathara.exceptions import PrivilegeError
from src.Kathara.types import SharedCollisionDomainsOption


#
# FIXTURE
#
@pytest.fixture()
def default_link():
    lab = Lab("default_scenario")
    lab.hash = "lab-hash"
    return lab.new_link("A")


@pytest.fixture()
def bridged_link():
    from src.Kathara.model.Link import Link
    lab = Lab("default_scenario")
    lab.hash = "lab-hash"
    return Link(lab, BRIDGE_LINK_NAME)


@pytest.fixture()
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin")
@mock.patch("docker.DockerClient")
def docker_link(mock_obj, mock_docker_plugin):
    return DockerLink(mock_obj, mock_docker_plugin)


@pytest.fixture()
@mock.patch("docker.models.networks.Network")
def docker_network(mock_network):
    return mock_network


@pytest.fixture()
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin")
@mock.patch("docker.DockerClient")
def docker_link(mock_docker_client, mock_docker_plugin):
    return DockerLink(mock_docker_client, mock_docker_plugin)


#
# TEST: get_network_name
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_network_name(mock_get_current_user_name, mock_setting_get_instance, default_link):
    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'net_prefix': 'kathara',
        'remote_url': None,
    })
    mock_setting_get_instance.return_value = setting_mock
    link_name = DockerLink.get_network_name(default_link)
    assert link_name == "kathara_user_A_lab-hash"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_network_name_shared_cds_between_labs(mock_get_current_user_name, mock_setting_get_instance, default_link):
    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.LABS,
        'net_prefix': 'kathara',
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock
    link_name = DockerLink.get_network_name(default_link)
    assert link_name == "kathara_user_A"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_network_name_shared_cds_between_users(mock_get_current_user_name, mock_setting_get_instance, default_link):
    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.USERS,
        'net_prefix': 'kathara',
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock
    link_name = DockerLink.get_network_name(default_link)
    assert link_name == "kathara_A"


#
# TEST: create
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create(mock_get_current_user_name, mock_setting_get_instance, docker_link, default_link):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'net_prefix': 'kathara',
        'remote_url': None,
        'network_plugin': 'kathara/katharanp'
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_user_A_lab-hash",
        driver=f"{setting_mock.network_plugin}:{utils.get_architecture()}",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "name": "A",
            "app": "kathara",
            "external": "",
            "user": "user",
            "lab_hash": default_link.lab.hash,
        }
    )


@mock.patch("src.Kathara.os.Networking.Networking.attach_interface_bridge")
@mock.patch("src.Kathara.os.Networking.Networking.get_or_new_interface")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.utils.is_platform")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_external(mock_get_current_user_name, mock_setting_get_instance, mock_is_platform,
                         mock_is_admin, mock_networking_get_intf, mock_networking_attach, docker_link, default_link):
    mock_networking_get_intf.return_value = 1

    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'net_prefix': 'kathara',
        'remote_url': None,
        'network_plugin': 'kathara/katharanp'
    })
    mock_setting_get_instance.return_value = setting_mock
    mock_is_platform.return_value = True
    mock_is_admin.return_value = True
    external_link = ExternalLink("eth0")
    default_link.lab.attach_external_links({"A": [external_link]})

    docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_user_A_lab-hash",
        driver=f"{setting_mock.network_plugin}:{utils.get_architecture()}",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "name": "A",
            "app": "kathara",
            "external": "eth0",
            "user": "user",
            "lab_hash": default_link.lab.hash,
        }
    )

    mock_networking_get_intf.assert_called_once_with("eth0", "eth0", None)
    docker_link.docker_plugin.exec_by_version.assert_called_once()


@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.utils.is_platform")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_external_os_error(mock_get_current_user_name, mock_setting_get_instance, mock_is_platform,
                                  mock_is_admin, docker_link, default_link):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'net_prefix': 'kathara',
        'remote_url': None,
        'network_plugin': 'kathara/katharanp'
    })
    mock_setting_get_instance.return_value = setting_mock
    mock_is_platform.return_value = False
    mock_is_admin.return_value = True
    external_link = ExternalLink("eth0")
    default_link.lab.attach_external_links({"A": [external_link]})

    with pytest.raises(OSError):
        docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_user_A_lab-hash",
        driver=f"{setting_mock.network_plugin}:{utils.get_architecture()}",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "name": "A",
            "app": "kathara",
            "external": "eth0",
            "user": "user",
            "lab_hash": default_link.lab.hash,
        }
    )


@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.utils.is_platform")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_external_privilege_error(mock_get_current_user_name, mock_setting_get_instance, mock_is_platform,
                                         mock_is_admin, docker_link, default_link):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'net_prefix': 'kathara',
        'remote_url': None,
        'network_plugin': 'kathara/katharanp'
    })
    mock_setting_get_instance.return_value = setting_mock
    mock_is_platform.return_value = True
    mock_is_admin.return_value = False
    external_link = ExternalLink("eth0")
    default_link.lab.attach_external_links({"A": [external_link]})

    with pytest.raises(PrivilegeError):
        docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_user_A_lab-hash",
        driver=f"{setting_mock.network_plugin}:{utils.get_architecture()}",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "name": "A",
            "app": "kathara",
            "external": "eth0",
            "user": "user",
            "lab_hash": default_link.lab.hash,
        }
    )


def test_create_bridge_link(docker_link, bridged_link):
    assert not docker_link.create(bridged_link)


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_shared_cds_between_users(mock_get_current_user_name, mock_setting_get_instance, docker_link,
                                         default_link):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.USERS,
        'net_prefix': 'kathara',
        'remote_url': None,
        'network_plugin': 'kathara/katharanp'
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_A",
        driver=f"{setting_mock.network_plugin}:{utils.get_architecture()}",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "name": "A",
            "app": "kathara",
            "external": ""
        }
    )


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_shared_cds_between_labs(mock_get_current_user_name, mock_setting_get_instance, docker_link,
                                        default_link):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.LABS,
        'net_prefix': 'kathara',
        'remote_url': None,
        'network_plugin': 'kathara/katharanp'
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_user_A",
        driver=f"{setting_mock.network_plugin}:{utils.get_architecture()}",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "name": "A",
            "user": "user",
            "app": "kathara",
            "external": ""
        }
    )


#
# TEST: _deploy_link
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.create")
def test_deploy_link(mock_create, docker_link, default_link):
    docker_link._deploy_link(("", default_link))
    mock_create.called_once_with(default_link)


def test_deploy_link_bridge(docker_link, bridged_link):
    assert not docker_link._deploy_link((bridged_link.name, bridged_link))


#
# TEST: deploy_links
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._deploy_link")
def test_deploy_links(mock_deploy_link, docker_link):
    lab = Lab("Default scenario")
    link_a = lab.get_or_new_link("A")
    link_b = lab.get_or_new_link("B")
    link_c = lab.get_or_new_link("C")
    docker_link.deploy_links(lab)
    mock_deploy_link.assert_any_call(("A", link_a))
    mock_deploy_link.assert_any_call(("B", link_b))
    mock_deploy_link.assert_any_call(("C", link_c))
    assert mock_deploy_link.call_count == 3


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._deploy_link")
def test_deploy_links_no_link(mock_deploy_link, docker_link):
    lab = Lab("Default scenario")
    docker_link.deploy_links(lab)
    assert not mock_deploy_link.called


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._deploy_link")
def test_deploy_links_selected_links(mock_deploy_link, docker_link):
    lab = Lab("Default scenario")
    link_a = lab.get_or_new_link("A")
    link_b = lab.get_or_new_link("B")
    link_c = lab.get_or_new_link("C")
    docker_link.deploy_links(lab, selected_links={"A"})
    mock_deploy_link.assert_any_call(("A", link_a))
    assert call(("B", link_b)) not in mock_deploy_link.mock_calls
    assert call(("C", link_c)) not in mock_deploy_link.mock_calls
    assert mock_deploy_link.call_count == 1


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._deploy_link")
def test_deploy_links_excluded_links(mock_deploy_link, docker_link):
    lab = Lab("Default scenario")
    link_a = lab.get_or_new_link("A")
    link_b = lab.get_or_new_link("B")
    link_c = lab.get_or_new_link("C")
    docker_link.deploy_links(lab, excluded_links={"A"})
    assert call(("A", link_a)) not in mock_deploy_link.mock_calls
    mock_deploy_link.assert_any_call(("B", link_b))
    mock_deploy_link.assert_any_call(("C", link_c))
    assert mock_deploy_link.call_count == 2


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._deploy_link")
def test_deploy_links_selected_and_excluded_links(mock_deploy_link, docker_link):
    lab = Lab("Default scenario")
    link_a = lab.get_or_new_link("A")
    link_b = lab.get_or_new_link("B")
    link_c = lab.get_or_new_link("C")
    docker_link.deploy_links(lab, selected_links={"A", "B"}, excluded_links={"B"})
    mock_deploy_link.assert_any_call(("A", link_a))
    assert call(("B", link_b)) not in mock_deploy_link.mock_calls
    assert call(("C", link_c)) not in mock_deploy_link.mock_calls
    assert mock_deploy_link.call_count == 1

#
# TEST: _delete_link
#
@mock.patch("docker.models.networks.Network")
def test_delete_link(docker_network, docker_link):
    docker_network.attrs = {"Labels": {"external": ""}}
    docker_link._delete_link(docker_network)
    docker_network.remove.assert_called_once()


#
# TEST: _undeploy_link
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
def test_undeploy_link(mock_undeploy_link, docker_link, docker_network):
    docker_link._undeploy_link(docker_network)
    mock_undeploy_link.called_once_with(docker_network)


#
# TEST: test_get_links_by_filters
#
@mock.patch("docker.models.networks.list")
def test_get_links_by_filters(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters("lab_hash_value", "link_name_value", "user_name_value")
    filters = {"label": ["app=kathara", "lab_hash=lab_hash_value", "user=user_name_value", "name=link_name_value"]}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_empty_filters(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters()
    filters = {"label": ["app=kathara"]}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_only_lab_hash(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters("lab_hash_value")
    filters = {"label": ["app=kathara", "lab_hash=lab_hash_value"]}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_only_link_name(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters(None, "link_name_value")
    filters = {"label": ["app=kathara", "name=link_name_value"]}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_only_user_name(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters(None, None, "user_name_value")
    filters = {"label": ["app=kathara", "user=user_name_value"]}
    mock_network_list.called_once_with(filters=filters)


#
# TEST: undeploy
#
@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_undeploy(mock_get_links_by_filters, mock_undeploy_link, mock_net1, mock_net2, mock_net3,
                  docker_link):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")
    lab.get_or_new_link("C")
    mock_get_links_by_filters.return_value = [mock_net1, mock_net2, mock_net3]
    docker_link.undeploy("lab_hash")
    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_net1.reload.call_count == 1
    assert mock_net2.reload.call_count == 1
    assert mock_net3.reload.call_count == 1
    assert mock_undeploy_link.call_count == 3


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_undeploy_empty_lab(mock_get_links_by_filters, mock_undeploy_link, docker_link):
    lab = Lab("Default scenario")
    mock_get_links_by_filters.return_value = []
    docker_link.undeploy("lab_hash")
    mock_get_links_by_filters.called_once_with(lab.hash)
    assert not mock_undeploy_link.called


@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_undeploy_selected_links(mock_get_links_by_filters, mock_undeploy_link, mock_net1, mock_net2, docker_link):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")

    mock_net1.attrs = {"Labels": {"name": "A"}}
    mock_net2.attrs = {"Labels": {"name": "B"}}

    mock_get_links_by_filters.return_value = [mock_net1, mock_net2]

    docker_link.undeploy("lab_hash", selected_links={"B"})
    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_net1.reload.call_count == 0
    assert mock_net2.reload.call_count == 1
    assert mock_undeploy_link.call_count == 1


#
# TEST: wipe
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_wipe(mock_get_links_by_filters, mock_net1, mock_net2, mock_net3, mock_undeploy_link, docker_link):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")
    lab.get_or_new_link("C")
    mock_get_links_by_filters.return_value = [mock_net1, mock_net2, mock_net3]
    docker_link.wipe()
    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_net1.reload.call_count == 1
    assert mock_net2.reload.call_count == 1
    assert mock_net3.reload.call_count == 1
    assert mock_undeploy_link.call_count == 3


#
# TEST: get_links_stats
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash(mock_get_links_api_objects_by_filters, docker_link,
                                  docker_network):
    docker_network.api_object.name = "test_network"
    mock_get_links_api_objects_by_filters.return_value = [docker_network.api_object]
    stat = next(docker_link.get_links_stats(lab_hash="lab_hash", user="user"))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name=None, user="user")
    assert stat['test_network']
    assert stat['test_network'].network_name == "test_network"


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_link_name(mock_get_links_api_objects_by_filters, docker_link,
                                            docker_network):
    docker_network.api_object.name = "test_network"
    mock_get_links_api_objects_by_filters.return_value = [docker_network.api_object]
    next(docker_link.get_links_stats(lab_hash="lab_hash", link_name="test_network", user="user"))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name="test_network",
                                                                  user="user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_link_name_user(mock_get_links_api_objects_by_filters,
                                                 docker_link, docker_network):
    docker_network.api_object.name = "test_network"

    mock_get_links_api_objects_by_filters.return_value = [docker_network.api_object]
    next(docker_link.get_links_stats(lab_hash="lab_hash", link_name="test_network", user="kathara-user"))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name="test_network",
                                                                  user="kathara-user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_link_not_found(mock_get_links_api_objects_by_filters, docker_link,
                                                 docker_network):
    docker_network.api_object.name = "test_network"
    mock_get_links_api_objects_by_filters.return_value = []
    assert next(docker_link.get_links_stats(lab_hash="lab_hash", user="user")) == {}
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name=None, user="user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_link_name_not_found(mock_get_links_api_objects_by_filters, docker_link,
                                                      docker_network):
    docker_network.api_object.name = "test_network"
    mock_get_links_api_objects_by_filters.return_value = []
    assert next(docker_link.get_links_stats(lab_hash="lab_hash", link_name="test_network", user="user")) == {}
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name="test_network",
                                                                  user="user")


@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_no_user(mock_get_links_api_objects_by_filters, mock_is_admin, docker_link,
                                          docker_network):
    docker_network.api_object.name = "test_device"
    mock_get_links_api_objects_by_filters.return_value = [docker_network.api_object]
    mock_is_admin.return_value = True
    next(docker_link.get_links_stats(lab_hash="lab_hash", user=None))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name=None, user=None)


@mock.patch("src.Kathara.utils.is_admin")
def test_get_links_stats_privilege_error(mock_is_admin, docker_link):
    mock_is_admin.return_value = False
    with pytest.raises(PrivilegeError):
        next(docker_link.get_links_stats(lab_hash="lab_hash", link_name="test_device", user=None))
