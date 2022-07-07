from lazydocs import generate_docs

ignored_modules = [
    "Kathara.version", "Kathara.auth", "Kathara.cli", "Kathara.event", "Kathara.foundation",
    "Kathara.manager.docker.terminal", "Kathara.manager.kubernetes.terminal", "Kathara.os",
    "Kathara.parser", "Kathara.test", "Kathara.trdparty", "Kathara.validator", "Kathara.kathara", "Kathara.decorators",
    "Kathara.exceptions", "Kathara.strings", "Kathara.utils", "Kathara.webhooks", "kathara"
]

generate_docs(["../../src"], src_base_url="https://github.com/KatharaFramework/Kathara/tree/master", output_path="./docs",
              ignored_modules=ignored_modules,
              overview_file="Kathara-API-Docs.md", remove_package_prefix=False)
