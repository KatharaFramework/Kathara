def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true or false.

    Args:
        val (str): The value to convert. True values are 'y', 'yes', 't', 'true', 'on', and '1';
            false values are 'n', 'no', 'f', 'false', 'off', and '0'.

        Returns:
            bool: The value converted to bool.

        Raises:
            ValueError: If the specified value is not a valid representation of truth.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError(f"Invalid truth value `{val}`.")
