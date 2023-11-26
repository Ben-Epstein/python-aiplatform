# -*- coding: utf-8 -*-

# Copyright 2023 Google LLC
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

from google.cloud import aiplatform
from ray.job_submission import JobSubmissionClient
from tests.system.aiplatform import e2e_base
import os
import ray
import time
import tempfile

RAY_VERSION = "2.4.0"
CLUSTER_RAY_VERSION = "2_4"
PROJECT_ID = "ucaip-sample-tests"
DASHBOARD_ADDRESS = (
    "3bc94b5d968a5971-dot-us-central1.aiplatform-training.googleusercontent.com"
)


class TestJobSubmissionDashboard(e2e_base.TestEndToEnd):
    _temp_prefix = "temp-job-submission-dashboard"

    def test_job_submission_dashboard(self):
        assert ray.__version__ == RAY_VERSION
        aiplatform.init(project=PROJECT_ID, location="us-central1")

        # Connect to cluster
        client = JobSubmissionClient("vertex_ray://{}".format(DASHBOARD_ADDRESS))

        my_script = """
        import ray
        import time

        @ray.remote
        def hello_world():
            return "hello world"

        @ray.remote
        def square(x):
            print(x)
            time.sleep(100)
            return x * x

        ray.init()  # No need to specify address="vertex_ray://...."
        print(ray.get(hello_world.remote()))
        print(ray.get([square.remote(i) for i in range(4)]))
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create my_script.py file
            fp = os.path.join(temp_dir, "my_script.py")
            f = open(fp, "w")
            f.write(my_script)
            f.close()

            job_id = client.submit_job(
                # Entrypoint shell command to execute
                entrypoint="python my_script.py",
                # Path to the local directory that contains the my_script.py file
                runtime_env={"working_dir": temp_dir},
            )

            job_status = None
            while job_status != ray.job_submission.JobStatus.SUCCEEDED:
                job_status = client.get_job_info(job_id).status
                print(job_id, "has status:", job_status)
                if (
                    job_status == ray.job_submission.JobStatus.PENDING
                    or job_status == ray.job_submission.JobStatus.RUNNING
                ):
                    time.sleep(10)
                elif (
                    job_status == ray.job_submission.JobStatus.FAILED
                    or job_status == ray.job_submission.JobStatus.STOPPED
                ):
                    print(job_id, "job logs:")
                    print(client.get_job_info(job_id).message)
                    raise RuntimeError("The Ray Job encountered an error and failed")