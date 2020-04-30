import re


def flatten_html(body: str) -> str:
    """
    Remove whitespace around html element tags.
    """
    # remove whitespace after html tags
    flat = re.sub(r"\>\s+", ">", body)
    # remove whitespace before html tags
    flat = re.sub(r"\s+\<", "<", flat)
    return flat


def body_has_element_with_attributes(body: str, attributes: dict) -> bool:
    element_pattern = r"(\<[^\>]+\>)"
    matches = re.findall(element_pattern, body)
    found_matching_element = False
    for element in matches:
        attributes_found = {}
        for attribute_name, attribute_value in attributes.items():
            if attribute_value:
                find_string = f'{attribute_name}="{attribute_value}"'
            else:
                find_string = attribute_name

            attributes_found[attribute_name] = find_string in element

        # You don't want to assign the variable directly
        if all(attributes_found.values()):
            found_matching_element = True
            # You only need one match
            break

    return found_matching_element
