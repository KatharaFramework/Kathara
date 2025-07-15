import os
from lazydocs import generate_docs

ignored_modules = [
    "Kathara.version", "Kathara.auth", "Kathara.cli", "Kathara.trdparty", "Kathara.foundation.cli",
    "Kathara.foundation.test", "Kathara.foundation.setting", "Kathara.exceptions", "Kathara.webhooks",
    "Kathara.validator", "Kathara.test", "kathara",
    "Kathara.manager.kubernetes.terminal.KubernetesWSTerminal", "Kathara.foundation.factory",
    "Kathara.manager.docker.terminal.DockerTTYTerminal",
    "Kathara.foundation.manager.terminal.Terminal", "Kathara.foundation.manager.ManagerFactory",
    "Kathara.foundation.setting.SettingsAddon", "Kathara.foundation.setting.SettingsAddonFactory",
    "Kathara.setting.addon.DockerSettingsAddon", "Kathara.setting.addon.KubernetesSettingsAddon"
]

generate_docs(["../../src"],
              src_base_url="https://github.com/KatharaFramework/Kathara/tree/main", output_path="./docs",
              ignored_modules=ignored_modules,
              overview_file="Kathara-API-Docs.md", remove_package_prefix=False)
