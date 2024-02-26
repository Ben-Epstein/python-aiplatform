#!/bin/bash
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -eo pipefail

if [[ -z "${PROJECT_ROOT:-}" ]]; then
    PROJECT_ROOT="${KOKORO_ARTIFACTS_DIR}/github/python-aiplatform"
fi

cd "${PROJECT_ROOT}"
mkdir -p output

# Disable buffering, so that the logs stream through.
export PYTHONUNBUFFERED=1

# Debug: show build environment
env | grep KOKORO

# Setup service account credentials.
export GOOGLE_APPLICATION_CREDENTIALS=${KOKORO_GFILE_DIR}/service-account.json

# Setup project id.
export PROJECT_ID=$(cat "${KOKORO_GFILE_DIR}/project-id.json")

# Remove old nox
python3 -m pip uninstall --yes --quiet nox-automation

# Install nox
python3 -m pip install --upgrade --quiet nox
python3 -m nox --version

# If this is a continuous build, send the test log to the FlakyBot.
# See https://github.com/googleapis/repo-automation-bots/tree/main/packages/flakybot.
if [[ $KOKORO_BUILD_ARTIFACTS_SUBDIR = *"continuous"* ]]; then
  cleanup() {
    chmod +x $KOKORO_GFILE_DIR/linux_amd64/flakybot
    $KOKORO_GFILE_DIR/linux_amd64/flakybot
  }
  trap cleanup EXIT HUP
fi

if [[ $KOKORO_BUILD_ARTIFACTS_SUBDIR = *"continuous"* ]]; then
  echo "====.  continuous"
  SPONGE_FILE_NAME="sponge_log.xml"
fi

if [[ $KOKORO_BUILD_ARTIFACTS_SUBDIR = *"presubmit"* ]]; then
  echo "====.  presubmit"
  SPONGE_FILE_NAME="sponge_log.xml"
fi

# If NOX_SESSION is set, it only runs the specified session,
# otherwise run all the sessions.
if [[ -n "${NOX_SESSION:-}" ]]; then
    python3 -m nox -s ${NOX_SESSION:-}
else
    python3 -m nox
fi

echo "===== TEST KOKORO_ARTIFACTS_DIR ======"
pwd
echo "===== ls -R $KOKORO_ARTIFACTS_DIR ======"
ls -R $KOKORO_ARTIFACTS_DIR

if [[ -e "${SPONGE_FILE_NAME}" ]]; then
  echo "====== file exists... copying... ======"
  cp sponge_log.xml output/sponge_log.xml
  chmod -R -x+X output/sponge_log.xml
  ls -lR $KOKORO_ARTIFACTS_DIR
fi
