import requests
import ast


def extract_python_code(response_text: str):
    """
    Extract and remove text within ````output ... ``` markers, while keeping the text within ````python ... ``` markers.

    :param response_text: The string containing the code and output blocks.
    :return: A tuple containing the extracted Python code and the modified string with the output block removed.
    """
    extracted_python = []
    modified_response_text = []
    in_python_block = False
    in_output_block = False
    last_boxed_sentence = None

    for line in response_text.split("\n"):
        if line.strip() == "```python":
            in_python_block = True
            extracted_python = []  # Reset the list to only keep the last Python block
        elif line.strip() == "```output":
            in_output_block = True
        elif line.strip() == "```":
            in_python_block = False
            in_output_block = False
        elif in_python_block:
            extracted_python.append(line)
        elif not in_output_block:
            if "\\boxed{" in line:
                last_boxed_sentence = line
            else:
                modified_response_text.append(line)

    extracted_python_text = "\n".join(extracted_python)
    modified_response_text = "\n".join(modified_response_text)

    return extracted_python_text, modified_response_text, last_boxed_sentence


def get_last_assigned_variable_name_and_value(code):
    # Parse the code into an AST
    tree = ast.parse(code)

    # Traverse the AST to find the last assignment statement
    last_assignment = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            last_assignment = node

    # Extract the name of the last assigned variable
    if last_assignment:
        last_var_name = last_assignment.targets[0].id
    else:
        return None, None

    # Execute the code to create the variables in the local namespace
    local_vars = {}
    exec(code, {}, local_vars)

    # Retrieve the value of the last assigned variable
    last_var_value = local_vars.get(last_var_name)

    return last_var_name, last_var_value


def compute_by_llm_tir(query):
    messages = [
        {
            "role": "system",
            "content": "You will assist in solving math word problems. Please integrate natural language reasoning with programs to solve the problems, and put your final answer within \\boxed{}.",
        },
        {
            "role": "user",
            "content": f"{query}\n\nImportant: When writing the python code, ALWAYS store the final answer in the 'answer' variable.",
        },
    ]

    payload = {
        "task": "math",
        "messages": messages,
        "temperature": 0.1,
    }

    inference_server_url = "http://0.0.0.0:8001"
    response = requests.post(f"{inference_server_url}/inference", json=payload)

    if response.status_code == 200:
        res_data = response.json()
        return res_data["message"]
    else:
        print(f"Request failed with status code: {response.status_code}")
        print(f"Response Text: {response.text}")
        return None


def solution_pipeline(query, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = compute_by_llm_tir(query)

            python_code, modified_response, last_boxed_sentence = extract_python_code(
                response
            )

            _, last_var_value = get_last_assigned_variable_name_and_value(python_code)

            return python_code, modified_response, last_boxed_sentence, last_var_value
        except SyntaxError:
            if attempt < max_retries - 1:
                continue
            else:
                raise
