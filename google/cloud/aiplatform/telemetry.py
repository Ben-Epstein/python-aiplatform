# -*- coding: utf-8 -*-

# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from google.cloud.aiplatform import initializer
import contextlib


@contextlib.contextmanager
def tool_context_manager(tool_context: str) -> None:
    """Context manager for appending tool context to client instantiations.

    Example Usage:

        aiplatform.init(...)
        with telemetry.tool_context_manager('ClientName'):
            model = GenerativeModel("gemini-pro")
            responses = model.generate_content("Why is the sky blue?", stream=True)

    Args:
        tool_context: The name of the client library to attribute usage to

    Returns:
        None
    """
    _append_tool_context(tool_context)
    try:
        yield
    finally:
        _pop_tool_context(tool_context)


def _append_tool_context(tool_context: str) -> None:
    initializer.global_config._tool_contexts_to_append.append(tool_context)


def _pop_tool_context(tool_context: str) -> None:
    popped_tool_context = initializer.global_config._tool_contexts_to_append.pop()

    if popped_tool_context != tool_context:
        raise RuntimeError(
            "Tool context error detected. This can occur due to parallelization."
        )
