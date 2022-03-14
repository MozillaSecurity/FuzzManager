"""
ProgramConfiguration -- Configuration of a target program

Container class that stores various configuration parameters, like platform,
product, OS, version and other parameters relevant for reproducing the issue.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

from __future__ import annotations

import os
import sys

from FTB.ConfigurationFiles import ConfigurationFiles


class ProgramConfiguration:
    def __init__(
        self,
        product: str,
        platform: str,
        os: str,
        version: str | None = None,
        env: dict[str, str] | None = None,
        args: list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ):
        """
        @param product: The name of the product/program/branch tested
        @param platform: Platform on which is tested (e.g. x86, x86-64 or arm)
        @param os: Operating system on which is tested (e.g. linux, windows, macosx)
        """
        self.product = product.lower()
        self.platform = platform.lower()
        self.os = os.lower()
        self.version = version

        if env is None:
            env = {}

        if args is None:
            args = []

        if metadata is None:
            metadata = {}

        assert isinstance(env, dict)
        assert isinstance(args, list)
        assert isinstance(metadata, dict)

        self.env = env
        self.args = args
        self.metadata = metadata

    @staticmethod
    def fromBinary(binaryPath: str) -> ProgramConfiguration | None:
        binaryConfig = f"{binaryPath}.fuzzmanagerconf"
        if not os.path.exists(binaryConfig):
            print(
                f"Warning: No binary configuration found at {binaryConfig}",
                file=sys.stderr,
            )
            return None

        config = ConfigurationFiles([binaryConfig])
        mainConfig = config.mainConfig

        for field in ["product", "platform", "os"]:
            if field not in mainConfig:
                raise RuntimeError(
                    f'Missing "{field}" in binary configuration file {binaryConfig}'
                )

        # Version field is optional
        version = None
        if "product_version" in mainConfig:
            version = mainConfig["product_version"]

        return ProgramConfiguration(
            mainConfig["product"],
            mainConfig["platform"],
            mainConfig["os"],
            version=version,
            metadata=config.metadataConfig,
        )

    def addEnvironmentVariables(self, env: dict[str, str]) -> None:
        """
        Add (additional) environment variable definitions. Existing definitions
        will be overwritten if they are redefined in the given environment.

        @param env: Dictionary containing the environment variables
        """
        assert isinstance(env, dict)
        self.env.update(env)

    def addProgramArguments(self, args: list[str]) -> None:
        """
        Add (additional) program arguments.

        @param args: List containing the program arguments
        """
        assert isinstance(args, list)
        self.args.extend(args)

    def addMetadata(self, metadata: dict[str, object]) -> None:
        """
        Add (additional) metadata definitions. Existing definitions
        will be overwritten if they are redefined in the given metadata.

        @param metadata: Dictionary containing the metadata
        """
        assert isinstance(metadata, dict)
        self.metadata.update(metadata)
