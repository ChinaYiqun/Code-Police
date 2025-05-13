"""
CI/CD Integration Module for CodePolice
Provides adapters for popular CI platforms
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CIEnvironment:
    """CI environment metadata"""
    name: str
    is_ci: bool
    repo_path: Path
    output_dir: Path = Path("codepolice_reports")


class CICDAdapter:
    """
    Base class for CI/CD platform adapters
    """

    def __init__(self):
        self.env = self._detect_environment()

    def _detect_environment(self) -> CIEnvironment:
        """Detect current CI environment"""
        if "GITHUB_ACTIONS" in os.environ:
            return CIEnvironment(
                name="github",
                is_ci=True,
                repo_path=Path(os.environ.get("GITHUB_WORKSPACE", ".")),
                output_dir=Path("/tmp/codepolice")
            )
        elif "GITLAB_CI" in os.environ:
            return CIEnvironment(
                name="gitlab",
                is_ci=True,
                repo_path=Path(os.environ.get("CI_PROJECT_DIR", ".")),
                output_dir=Path("/tmp/codepolice")
            )
        elif "CIRCLECI" in os.environ:
            return CIEnvironment(
                name="circleci",
                is_ci=True,
                repo_path=Path(os.environ.get("CIRCLE_WORKING_DIRECTORY", ".")),
                output_dir=Path("/tmp/codepolice")
            )
        else:
            return CIEnvironment(
                name="local",
                is_ci=False,
                repo_path=Path("."),
                output_dir=Path("reports/codepolice")
            )

    def setup_environment(self) -> None:
        """Prepare CI environment for execution"""
        # Create output directory
        self.env.output_dir.mkdir(parents=True, exist_ok=True)

        # Set environment variables
        os.environ["CODEPOLICE_OUTPUT"] = str(self.env.output_dir)

    def generate_config(self) -> str:
        """Generate CI configuration file (to be implemented by subclasses)"""
        raise NotImplementedError("Must implement generate_config() in subclass")

    def process_results(self) -> None:
        """Process and report results (to be implemented by subclasses)"""
        raise NotImplementedError("Must implement process_results() in subclass")


class GitHubActionsAdapter(CICDAdapter):
    """
    GitHub Actions Adapter for CodePolice
    """

    def generate_config(self) -> str:
        """Generate GitHub Actions workflow file"""
        return f"""name: CodePolice Analysis
on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  codepolice-check:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'

    - name: Install CodePolice
      run: pip install codepolice

    - name: Run CodePolice Analysis
      run: codepolice check . --format json --output {self.env.output_dir}/results.json

    - name: Upload Report
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: codepolice-report
        path: {self.env.output_dir}
"""

    def process_results(self) -> None:
        """Process results in GitHub Actions context"""
        result_file = self.env.output_dir / "results.json"
        if result_file.exists():
            print("✅ CodePolice analysis completed")
            # Add GitHub Actions specific annotations here
        else:
            print("❌ No results file found")


class GitLabCIAdapter(CICDAdapter):
    """
    GitLab CI Adapter for CodePolice
    """

    def generate_config(self) -> str:
        """Generate GitLab CI configuration"""
        return f"""stages:
  - codepolice

codepolice_check:
  image: python:3
  script:
    - pip install codepolice
    - codepolice check . --format json --output {self.env.output_dir}/results.json
  artifacts:
    paths:
      - {self.env.output_dir}/
"""


class CircleCIAdapter(CICDAdapter):
    """
    CircleCI Adapter for CodePolice
    """

    def generate_config(self) -> str:
        """Generate CircleCI configuration"""
        return f"""version: 2.1
jobs:
  codepolice-check:
    docker:
      - image: python:3
    steps:
      - checkout
      - run:
          name: Install CodePolice
          command: pip install codepolice
      - run:
          name: Run CodePolice Analysis
          command: codepolice check . --format json --output {self.env.output_dir}/results.json
      - store_artifacts:
          path: {self.env.output_dir}
workflows:
  version: 2
  codepolice:
    jobs:
      - codepolice-check
"""


# Factory pattern for CI adapters
class CICDAdapterFactory:
    """
    Factory class to create appropriate CI adapter
    """

    @staticmethod
    def get_adapter() -> CICDAdapter:
        env = CICDAdapter()._detect_environment()
        if env.name == "github":
            return GitHubActionsAdapter()
        elif env.name == "gitlab":
            return GitLabCIAdapter()
        elif env.name == "circleci":
            return CircleCIAdapter()
        else:
            return CICDAdapter()