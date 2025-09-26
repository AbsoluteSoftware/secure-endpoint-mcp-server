import typing


def create_schema_fixing_component_fn(
    disable_validation: bool = False,
) -> typing.Callable:
    """
    Create a component function that disables schema validation for problematic OpenAPI specs.

    FastMCP calls this function during tool creation via the mcp_component_fn parameter. It allows
    us to modify each tool's configuration before it's finalized. By setting
    `component.output_schema = None`, we tell FastMCP to skip response validation for that tool
    while keeping the API call functionality intact.

    This is necessary because some OpenAPI specs have broken schema references that cause FastMCP's
    schema resolution to fail with "PointerToNowhere" errors, even though the actual API endpoints
    work fine.

    Args:
        disable_validation: If True, disable all output schema validation for all tools

    Returns:
        Function that can be passed as mcp_component_fn to FastMCP.from_openapi()

    Example:
        >>> component_fn = create_schema_fixing_component_fn(disable_validation=True)
        >>> server = FastMCP.from_openapi(spec, client, mcp_component_fn=component_fn)
    """

    def fix_component_schemas(route, component) -> None:  # type: ignore[no-untyped-def]
        """
        Disable schema validation entirely when flag is set.

        This function is called by FastMCP for each tool/component created from the OpenAPI spec.
        """
        if disable_validation and hasattr(component, "output_schema"):
            component.output_schema = None

    return fix_component_schemas
