#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
from typing import Optional, Tuple, Union

import click
import jsondiff
from openr.cli.utils import utils
from openr.cli.utils.commands import OpenrCtrlCmd
from openr.thrift.OpenrCtrl.thrift_types import OpenrError
from openr.thrift.OpenrCtrlCpp.thrift_clients import OpenrCtrlCpp as OpenrCtrlCppClient
from openr.thrift.Types import thrift_types as openr_types
from openr.utils import ipnetwork, printing
from openr.utils.consts import Consts
from thrift.python.serializer import deserialize


class ConfigShowCmd(OpenrCtrlCmd):
    async def _run(self, client: OpenrCtrlCppClient.Async, *args, **kwargs):
        resp = await client.getRunningConfig()
        config = json.loads(resp)
        utils.print_json(config)


class ConfigDryRunCmd(OpenrCtrlCmd):
    # pyre-fixme[14]: `_run` overrides method defined in `OpenrCtrlCmd` inconsistently.
    async def _run(
        self, client: OpenrCtrlCppClient.Async, file: str, *args, **kwargs
    ) -> int:
        try:
            file_conf = await client.dryrunConfig(file)
        except OpenrError as ex:
            click.echo(click.style("FAILED: {}".format(ex), fg="red"))
            return 1

        config = json.loads(file_conf)
        utils.print_json(config)
        return 0


class ConfigCompareCmd(OpenrCtrlCmd):
    # pyre-fixme[14]: `_run` overrides method defined in `OpenrCtrlCmd` inconsistently.
    async def _run(self, client: OpenrCtrlCppClient.Async, file: str, *args, **kwargs):
        running_conf = await client.getRunningConfig()

        try:
            file_conf = await client.dryrunConfig(file)
        except OpenrError as ex:
            click.echo(click.style("FAILED: {}".format(ex), fg="red"))
            return

        res = jsondiff.diff(running_conf, file_conf, load=True, syntax="explicit")
        if res:
            click.echo(click.style("DIFF FOUND!", fg="red"))
            print("== diff(running_conf, {}) ==".format(file))
            print(res)
        else:
            click.echo(click.style("SAME", fg="green"))


class ConfigStoreCmdBase(OpenrCtrlCmd):
    async def getConfigWrapper(
        self, client: OpenrCtrlCppClient.Async, config_key: str
    ) -> Tuple[Optional[bytes], Optional[str]]:
        blob = None
        exception_str = None
        try:
            blob = await client.getConfigKey(config_key)
        except OpenrError as ex:
            exception_str = "Exception getting key for {}: {}".format(config_key, ex)

        return (blob, exception_str)


class ConfigPrefixAllocatorCmd(ConfigStoreCmdBase):
    async def _run(self, client: OpenrCtrlCppClient.Async, *args, **kwargs):
        (prefix_alloc_blob, exception_str) = await self.getConfigWrapper(
            client, Consts.PREFIX_ALLOC_KEY
        )

        if prefix_alloc_blob is None:
            print(exception_str)
            return

        prefix_alloc = deserialize(openr_types.AllocPrefix, prefix_alloc_blob)
        self.print_config(prefix_alloc)

    def print_config(self, prefix_alloc: openr_types.AllocPrefix) -> None:
        seed_prefix = prefix_alloc.seedPrefix
        seed_prefix_addr = ipnetwork.sprint_addr(seed_prefix.prefixAddress.addr)

        caption = "Prefix Allocator parameters stored"
        rows = []
        rows.append(
            ["Seed prefix: {}/{}".format(seed_prefix_addr, seed_prefix.prefixLength)]
        )
        rows.append(["Allocated prefix length: {}".format(prefix_alloc.allocPrefixLen)])
        rows.append(
            ["Allocated prefix index: {}".format(prefix_alloc.allocPrefixIndex)]
        )

        print(printing.render_vertical_table(rows, caption=caption))


class ConfigLinkMonitorCmd(ConfigStoreCmdBase):
    async def _run(self, client: OpenrCtrlCppClient.Async, *args, **kwargs) -> None:
        # After link-monitor thread starts, it will hold for
        # "adjHoldUntilTimePoint_" time before populate config information.
        # During this short time-period, Exception can be hit if dump cmd
        # kicks during this time period.
        (lm_config_blob, exception_str) = await self.getConfigWrapper(
            client, Consts.LINK_MONITOR_KEY
        )

        if lm_config_blob is None:
            print(exception_str)
            return

        lm_config = deserialize(openr_types.LinkMonitorState, lm_config_blob)
        self.print_config(lm_config)

    def print_config(self, lm_config: openr_types.LinkMonitorState):
        caption = "Link Monitor parameters stored"
        rows = []
        rows.append(
            ["isOverloaded: {}".format("Yes" if lm_config.isOverloaded else "No")]
        )
        rows.append(
            ["overloadedLinks: {}".format(", ".join(lm_config.overloadedLinks))]
        )
        print(printing.render_vertical_table(rows, caption=caption))

        print(printing.render_vertical_table([["linkMetricOverrides:"]]))
        column_labels = ["Interface", "Metric Override"]
        rows = []
        for (k, v) in sorted(lm_config.linkMetricOverrides.items()):
            rows.append([k, v])
        print(printing.render_horizontal_table(rows, column_labels=column_labels))

        print(printing.render_vertical_table([["adjMetricOverrides:"]]))
        column_labels = ["Adjacency", "Metric Override"]
        rows = []
        for (k, v) in sorted(lm_config.adjMetricOverrides.items()):
            adj_str = k.nodeName + " " + k.ifName
            rows.append([adj_str, v])
        print(printing.render_horizontal_table(rows, column_labels=column_labels))


class ConfigPrefixManagerCmd(ConfigStoreCmdBase):
    async def _run(self, client: OpenrCtrlCppClient.Async, *args, **kwargs) -> None:
        (prefix_mgr_config_blob, exception_str) = await self.getConfigWrapper(
            client, Consts.PREFIX_MGR_KEY
        )

        if prefix_mgr_config_blob is None:
            print(exception_str)
            return

        prefix_mgr_config = deserialize(
            openr_types.PrefixDatabase, prefix_mgr_config_blob
        )
        self.print_config(prefix_mgr_config)

    def print_config(self, prefix_mgr_config: openr_types.PrefixDatabase):
        print()
        print(utils.sprint_prefixes_db_full(prefix_mgr_config))
        print()


class ConfigEraseCmd(ConfigStoreCmdBase):
    # pyre-fixme[14]: `_run` overrides method defined in `OpenrCtrlCmd` inconsistently.
    async def _run(
        self, client: OpenrCtrlCppClient.Async, key: str, *args, **kwargs
    ) -> None:
        await client.eraseConfigKey(key)
        print("Key:{} erased".format(key))


class ConfigStoreCmd(ConfigStoreCmdBase):
    # pyre-fixme[14]: `_run` overrides method defined in `OpenrCtrlCmd` inconsistently.
    async def _run(
        self,
        client: OpenrCtrlCppClient.Async,
        key: str,
        value: Union[bytes, str],
        *args,
        **kwargs,
    ) -> None:
        if isinstance(value, str):
            value = value.encode()
        await client.setConfigKey(key, value)
        print("Key:{}, value:{} stored".format(key, value))
