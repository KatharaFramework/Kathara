from lazydocs import generate_docs

ignored_modules = [
    "Kathara.version", "Kathara.auth", "Kathara.cli", "Kathara.connectors", "Kathara.foundation", "Kathara.os",
    "Kathara.parser", "Kathara.test", "Kathara.trdparty", "Kathara.validator", "Kathara.kathara", "Kathara.decorators",
    "Kathara.exceptions", "Kathara.strings", "Kathara.utils", "kathara"
]

generate_docs(["../../src"], src_root_path="../../src/", output_path="./docs",
              ignored_modules=ignored_modules,
              overview_file="Kathara-API-Docs.md", remove_package_prefix=False)
