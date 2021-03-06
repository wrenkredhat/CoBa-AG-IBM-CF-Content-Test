#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) IBM Corporation 2019, 2020
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: zos_operator_action_query
short_description: Display messages requiring action
description:
  - Get a list of outstanding messages requiring operator action given one or
    more conditions.
author:
  - "Ping Xiao (@xiaoping8385)"
  - "Demetrios Dimatos (@ddimatos)"
options:
  system:
    description:
        - Return outstanding messages requiring operator action awaiting a
          reply for a particular system.
        - If the system name is not specified, all outstanding messages for
          that system and for the local systems attached to it are returned.
        - A trailing asterisk, (*) wildcard is supported.
    type: str
    required: false
  message_id:
    description:
        - Return outstanding messages requiring operator action awaiting a
          reply for a particular message identifier.
        - If the message identifier is not specified, all outstanding messages
          for all message identifiers are returned.
        - A trailing asterisk, (*) wildcard is supported.
    type: str
    required: false
  job_name:
    description:
      - Return outstanding messages requiring operator action awaiting a reply
        for a particular job name.
      - If the message job name is not specified, all outstanding messages
        for all job names are returned.
      - A trailing asterisk, (*) wildcard is supported.
    type: str
    required: false
seealso:
- module: zos_operator
"""

EXAMPLES = r"""
- name: Display all outstanding messages issued on system MV2H
  zos_operator_action_query:
      system: mv2h

- name: Display all outstanding messages whose job name begin with im5
  zos_operator_action_query:
      job_name: im5*

- name: Display all outstanding messages whose message id begin with dsi*
  zos_operator_action_query:
      message_id: dsi*

- name: Display all outstanding messages given job_name, message_id, system
  zos_operator_action_query:
      job_name: mq*
      message_id: dsi*
      system: mv29
"""

RETURN = r"""
changed:
    description:
        Indicates if any changes were made during module operation. Given
        operator action commands query for messages, True is always returned
        unless either a module or command failure has occurred.
    returned: always
    type: bool
    sample: false
count:
    description:
        The total number of outstanding messages.
    returned: on success
    type: int
    sample: 12
actions:
    description:
        The list of the outstanding messages.
    returned: success
    type: list
    elements: dict
    contains:
        number:
            description:
                The message identification number.
            returned: on success
            type: int
            sample: 001
        type:
            description:
                The action type,'R' means request.
            returned: on success
            type: str
            sample: R
        system:
            description:
                System on which the outstanding message requiring operator
                action awaiting a reply.
            returned: on success
            type: str
            sample: MV27
        job_id:
            description:
                Job identifier for the outstanding message requiring operator
                action awaiting a reply.
            returned: on success
            type: str
            sample: STC01537
        message_text:
            description:
                Job identifier for outstanding message requiring operator
                action awaiting a reply.
            returned: success
            type: str
            sample: "*399 HWSC0000I *IMS CONNECT READY* IM5HCONN"
        job_name:
            description:
                Job name for outstanding message requiring operator action
                awaiting a reply.
            returned: success
            type: str
            sample: IM5HCONN
        message_id:
            description:
                Message identifier for outstanding message requiring operator
                action awaiting a reply.
            returned: success
            type: str
            sample: HWSC0000I
    sample:
        [
            {
                "number": '001',
                "type": 'R',
                "system": 'MV27',
                "job_id": 'STC01537',
                "message_text": '*399 HWSC0000I *IMS CONNECT READY* IM5HCONN',
                "job_name": 'IM5HCONN',
                "message_id": 'HWSC0000I'
            },
            {
                "number": '002',
                "type": 'R',
                "system": 'MV27',
                "job_id": 'STC01533',
                "message_text": '*400 DFS3139I IMS INITIALIZED, AUTOMATIC RESTART PROCEEDING IM5H',
                "job_name": 'IM5HCTRL',
                "message_id": 'DFS3139I'
            }
        ]
"""

from ansible.module_utils.basic import AnsibleModule
import re
from ansible_collections.ibm.ibm_zos_core.plugins.module_utils.better_arg_parser import (
    BetterArgParser,
)
from ansible_collections.ibm.ibm_zos_core.plugins.module_utils.import_handler import (
    MissingZOAUImport,
)

try:
    from zoautil_py import opercmd
except Exception:
    opercmd = MissingZOAUImport()


def run_module():
    module_args = dict(
        system=dict(type="str", required=False),
        message_id=dict(type="str", required=False),
        job_name=dict(type="str", required=False),
    )

    result = dict(changed=False)
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)
    requests = []
    try:
        new_params = parse_params(module.params)

        cmd_result_a = execute_command("d r,a,s")
        if cmd_result_a.rc > 0:
            module.fail_json(
                msg="A non-zero return code was received while querying the operator.",
                stdout=cmd_result_a.stdout,
                stderr=cmd_result_a.stderr,
                rc=cmd_result_a.rc,
                stdout_lines=cmd_result_a.stdout.splitlines() if cmd_result_a.stdout else None,
                stderr_lines=cmd_result_a.stderr.splitlines() if cmd_result_a.stderr else None,
                cmd="d r,a,s",
            )

        cmd_result_b = execute_command("d r,a,jn")
        if cmd_result_b.rc > 0:
            module.fail_json(
                msg="A non-zero return code was received while querying the operator.",
                stdout=cmd_result_b.stdout,
                stderr=cmd_result_b.stderr,
                rc=cmd_result_b.rc,
                stdout_lines=cmd_result_b.stdout.splitlines() if cmd_result_b.stdout else None,
                stderr_lines=cmd_result_b.stderr.splitlines() if cmd_result_b.stderr else None,
                cmd="d r,a,jn",
            )

        merged_list = create_merge_list(cmd_result_a.message, cmd_result_b.message)
        requests = find_required_request(merged_list, new_params)
        if requests:
            result["count"] = len(requests)
    except Error as e:
        module.fail_json(msg=repr(e), **result)
    except Exception as e:
        module.fail_json(
            msg="An unexpected error occurred: {0}".format(repr(e)), **result
        )

    result["actions"] = requests
    module.exit_json(**result)


def parse_params(params):
    arg_defs = dict(
        system=dict(arg_type=system_type, required=False),
        message_id=dict(arg_type=message_id_type, required=False),
        job_name=dict(arg_type=job_name_type, required=False),
    )
    parser = BetterArgParser(arg_defs)
    new_params = parser.parse_args(params)
    return new_params


def system_type(arg_val, params):
    regex = "^(?:[a-zA-Z0-9]{1,8})|(?:[a-zA-Z0-9]{0,7}[*])$"
    validate_parameters_based_on_regex(arg_val, regex)
    return arg_val.upper()


def message_id_type(arg_val, params):
    regex = "^(?:[a-zA-Z0-9]{1,})|(?:[a-zA-Z0-9]{0,}[*])$"
    validate_parameters_based_on_regex(arg_val, regex)
    return arg_val.upper()


def job_name_type(arg_val, params):
    regex = "^(?:[a-zA-Z0-9]{1,8})|(?:[a-zA-Z0-9]{0,7}[*])$"
    validate_parameters_based_on_regex(arg_val, regex)
    return arg_val.upper()


def validate_parameters_based_on_regex(value, regex):
    pattern = re.compile(regex)
    if pattern.fullmatch(value):
        pass
    else:
        raise ValidationError(str(value))
    return value


def find_required_request(merged_list, params):
    """Find the request given the options provided."""
    requests = filter_requests(merged_list, params)
    return requests


def create_merge_list(message_a, message_b):
    """Merge the return lists that execute both 'd r,a,s' and 'd r,a,jn'.
    For example, if we have:
    'd r,a,s' response like: "742 R MV28     JOB57578 &742 ARC0055A REPLY 'GO'OR 'CANCEL'"
    'd r,a,jn' response like:"742 R FVFNT29H &742 ARC0055A REPLY 'GO' OR 'CANCEL'"
    the results will be merged so that a full list of information returned on condition"""
    list_a = parse_result_a(message_a)
    list_b = parse_result_b(message_b)
    merged_list = merge_list(list_a, list_b)
    return merged_list


def filter_requests(merged_list, params):
    """filter the request given the params provided."""
    system = params.get("system")
    message_id = params.get("message_id")
    job_name = params.get("job_name")
    newlist = merged_list
    if system:
        newlist = handle_conditions(newlist, "system", system)
    if job_name:
        newlist = handle_conditions(newlist, "job_name", job_name)
    if message_id:
        newlist = handle_conditions(newlist, "message_id", message_id)
    return newlist


def handle_conditions(list, condition_type, value):
    # regex = re.compile(condition_values)
    newlist = []
    for dict in list:
        if value.endswith("*"):
            exist = dict.get(condition_type).startswith(value.rstrip("*"))
        else:
            exist = dict.get(condition_type) == value
        if exist:
            newlist.append(dict)
    return newlist


def execute_command(operator_cmd):

    response = opercmd.execute(operator_cmd)
    rc = response.rc
    stdout = response.stdout_response
    stderr = response.stderr_response
    return OperatorQueryResult(rc, stdout, stderr)


def parse_result_a(result):
    """parsing the result that coming from command 'd r,a,s',
    there are usually two formats:
     - line with job_id: 810 R MV2D     JOB58389 &810 ARC0055A REPLY 'GO' OR 'CANCEL'
     - line without job_id: 574 R MV28              *574 IXG312E OFFLOAD DELAYED FOR..
    also the request contains multiple lines, we need to handle that as well"""

    dict_temp = {}
    list = []

    match_iter = re.finditer(
        r"^\s*([0-9]{2,})\s([A-Z]{1})\s([A-Z0-9]{1,8})\s+((?:[A-Z0-9]{1,8})?)\s*[&*]?[0-9]+(.*)",
        result,
        re.MULTILINE,
    )
    for match in match_iter:
        dict_temp = {
            "number": match.group(1),
            "type": match.group(2),
            "system": match.group(3),
        }
        if match.group(4) != "":
            dict_temp["job_id"] = match.group(4)
        if match.group(5) != "":
            dict_temp["message_text"] = match.group(5).strip()
        list.append(dict_temp)

    return list


def parse_result_b(result):
    """Parse the result that comes from command 'd r,a,jn', the main purpose
    to use this command is to get the job_name and message id, which is not
    included in 'd r,a,s'"""

    dict_temp = {}
    list = []

    match_iter = re.finditer(
        r"^\s*([0-9]{2,})\s[A-Z]{1}\s+([A-Z0-9]{1,8})?\s*[&*]?[0-9]+\s([A-Z0-9]+)",
        result,
        re.MULTILINE,
    )

    for match in match_iter:
        dict_temp = {
            "number": match.group(1),
            "job_name": match.group(2),
            "message_id": match.group(3),
        }

        # Sometimes 'job_name' will be null because the operator action is a
        # WTOR like in a dump command so remove keys with None types
        dict_temp_result = {
            k: v for k, v in dict_temp.items() if (v is not None)}
        list.append(dict_temp_result)

    return list


def merge_list(list_a, list_b):
    merged_list = []
    for dict_a in list_a:
        for dict_b in list_b:
            if dict_a.get("number") == dict_b.get("number"):
                dict_z = dict_a.copy()
                dict_z.update(dict_b)
                merged_list.append(dict_z)
    return merged_list


class Error(Exception):
    pass


class ValidationError(Error):
    def __init__(self, message):
        self.msg = (
            'An error occurred during validate the input parameters: "{0}"'.format(
                message
            )
        )


class OperatorQueryResult:
    def __init__(
        self,
        rc,
        stdout,
        stderr
    ):
        """Response object class to manage the result from executing a command
        to query for actionable messages. Class will also generate a message
        by concatenating stdout and stderr

        Arguments:
            rc {str} -- The return code
            stdout {str} -- The standard out of the command run
            stderr {str} -- The standard error of the command run
        """
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        self.message = stdout


def main():
    run_module()


if __name__ == "__main__":
    main()
