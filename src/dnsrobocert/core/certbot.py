#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import logging
import os
import sys
from typing import List, Optional

import coloredlogs
from certbot import main

from dnsrobocert.core import config, utils

LOGGER = logging.getLogger(__name__)
coloredlogs.install(logger=LOGGER)

_DEFAULT_FLAGS = ["-n"]


def account(config_path: str, directory_path: str):
    dnsrobocert_config = config.load(config_path)
    acme = dnsrobocert_config.get("acme", {})
    email = acme.get("email_account")

    if not email:
        LOGGER.warning(
            "Parameter acme.email_account is not set, skipping ACME registration."
        )
        return

    url = config.get_acme_url(dnsrobocert_config)

    utils.execute(
        [
            sys.executable,
            "-m",
            "dnsrobocert.core.certbot",
            "register",
            *_DEFAULT_FLAGS,
            "--config-dir",
            directory_path,
            "--work-dir",
            os.path.join(directory_path, "workdir"),
            "--logs-dir",
            os.path.join(directory_path, "logs"),
            "-m",
            email,
            "--agree-tos",
            "--server",
            url,
        ],
        check=False,
    )


def certonly(
    config_path: str,
    directory_path: str,
    lineage: str,
    domains: Optional[List[str]] = None,
    force_renew: bool = False,
):
    if not domains:
        return

    url = config.get_acme_url(config.load(config_path))

    additional_params = []
    if force_renew:
        additional_params.append("--force-renew")

    for domain in domains:
        additional_params.append("-d")
        additional_params.append(domain)

    utils.execute(
        [
            sys.executable,
            "-m",
            "dnsrobocert.core.certbot",
            "certonly",
            *_DEFAULT_FLAGS,
            "--config-dir",
            directory_path,
            "--work-dir",
            os.path.join(directory_path, "workdir"),
            "--logs-dir",
            os.path.join(directory_path, "logs"),
            "--manual",
            "--preferred-challenges=dns",
            "--manual-auth-hook",
            _hook_cmd("auth", config_path, lineage),
            "--manual-cleanup-hook",
            _hook_cmd("cleanup", config_path, lineage),
            "--manual-public-ip-logging-ok",
            "--expand",
            "--deploy-hook",
            _hook_cmd("deploy", config_path, lineage),
            "--server",
            url,
            "--cert-name",
            lineage,
            *additional_params,
        ]
    )


def renew(config_path: str, directory_path: str):
    dnsrobocert_config = config.load(config_path)

    if dnsrobocert_config:
        utils.execute(
            [
                sys.executable,
                "-m",
                "dnsrobocert.core.certbot",
                "renew",
                *_DEFAULT_FLAGS,
                "--config-dir",
                directory_path,
                "--deploy-hook",
                _hook_cmd("deploy", config_path),
                "--work-dir",
                os.path.join(directory_path, "workdir"),
                "--logs-dir",
                os.path.join(directory_path, "logs"),
            ]
        )


def revoke(config_path: str, directory_path: str, lineage: str):
    url = config.get_acme_url(config.load(config_path))

    utils.execute(
        [
            sys.executable,
            "-m",
            "dnsrobocert.core.certbot",
            "revoke",
            "-n",
            "--config-dir",
            directory_path,
            "--work-dir",
            os.path.join(directory_path, "workdir"),
            "--logs-dir",
            os.path.join(directory_path, "logs"),
            "--server",
            url,
            "--cert-path",
            os.path.join(directory_path, "live", lineage, "cert.pem"),
        ]
    )


def _hook_cmd(hook_type: str, config_path: str, lineage: str = None) -> str:
    command = '{0} -m dnsrobocert.core.hooks -t {1} -c "{2}"'.format(
        sys.executable, hook_type, config_path
    )
    if lineage:
        command = '{0} -l "{1}"'.format(command, lineage)
    return command


if __name__ == "__main__":
    sys.exit(main.main())
