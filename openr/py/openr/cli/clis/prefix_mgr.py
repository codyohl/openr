#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


from typing import List, Optional

import bunch
import click
from openr.cli.clis.baseGroup import deduceCommandGroup
from openr.cli.commands import prefix_mgr
from openr.thrift.OpenrCtrl import thrift_types as ctrl_types


class PrefixMgrCli:
    def __init__(self):
        self.prefixmgr.add_command(WithdrawCli().withdraw)
        self.prefixmgr.add_command(AdvertiseCli().advertise)
        self.prefixmgr.add_command(SyncCli().sync)
        self.prefixmgr.add_command(AdvertisedRoutesCli().show)
        self.prefixmgr.add_command(OriginatedRoutesCli().show)
        self.prefixmgr.add_command(PrefixMgrValidateCli().validate)

    @click.group(cls=deduceCommandGroup)
    @click.pass_context
    def prefixmgr(ctx):  # noqa: B902
        """CLI tool to peek into Prefix Manager module."""
        pass


class WithdrawCli(object):
    @click.command()
    @click.argument("prefixes", nargs=-1)
    @click.option(
        "--prefix-type",
        "-t",
        default="BREEZE",
        help="Type or client-ID associated with prefix.",
    )
    @click.pass_obj
    def withdraw(
        cli_opts: bunch.Bunch, prefixes: List[str], prefix_type: str  # noqa: B902
    ):
        """Withdraw the prefixes being advertised from this node"""

        prefix_mgr.WithdrawCmd(cli_opts).run(prefixes, prefix_type)


class AdvertiseCli(object):
    @click.command()
    @click.argument("prefixes", nargs=-1)
    @click.option(
        "--prefix-type",
        "-t",
        default="BREEZE",
        help="Type or client-ID associated with prefix.",
    )
    @click.option(
        "--forwarding-type",
        default="IP",
        help="Use label forwarding instead of IP forwarding in data path",
    )
    @click.pass_obj
    def advertise(cli_opts, prefixes, prefix_type, forwarding_type):  # noqa: B902
        """Advertise the prefixes from this node with specific type"""

        prefix_mgr.AdvertiseCmd(cli_opts).run(prefixes, prefix_type, forwarding_type)


class SyncCli(object):
    @click.command()
    @click.argument("prefixes", nargs=-1)
    @click.option(
        "--prefix-type",
        "-t",
        default="BREEZE",
        help="Type or client-ID associated with prefix.",
    )
    @click.option(
        "--forwarding-type",
        default="IP",
        help="Use label forwarding instead of IP forwarding in data path",
    )
    @click.pass_obj
    def sync(cli_opts, prefixes, prefix_type, forwarding_type):  # noqa: B902
        """Sync the prefixes from this node with specific type"""

        prefix_mgr.SyncCmd(cli_opts).run(prefixes, prefix_type, forwarding_type)


class AdvertisedRoutesCli(object):
    @click.group("advertised-routes")
    @click.option(
        "--prefix-type",
        "-t",
        help="Filter on source of origination. e.g. RIB, BGP, LINK_MONITOR",
    )
    @click.option(
        "--detail/--no-detail",
        "-d/-D",
        default=True,
        help="Show all details including tags and area-stack",
    )
    @click.option(
        "--tag2name/--no-tag2name",
        "-n/-N",
        default=True,
        help="Translate tag string to human readable name",
    )
    @click.option("--json/--no-json", default=False, help="Output in JSON format")
    @click.pass_context
    def show(
        ctx: bunch.Bunch,  # noqa: B902
        prefix_type: Optional[str],
        detail: bool,
        tag2name: bool,
        json: bool,
    ) -> None:
        """
        Show advertised routes in various stages of policy
        """

        # Set options & arguments in cli_opts
        if ctx.obj is None:
            ctx.obj = bunch.Bunch()
        ctx.obj["advertised_routes_options"] = bunch.Bunch(
            prefix_type=prefix_type,
            detail=detail,
            json=json,
            tag2name=tag2name,
        )

    @show.command("all")
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def all(cli_opts: bunch.Bunch, prefix: List[str]) -> None:  # noqa: B902
        """
        Show routes that this node should be advertising across all areas. This
        is pre-area-policy routes. Note this does not show routes denied by origination policy
        """

        opts = cli_opts.advertised_routes_options
        prefix_mgr.AdvertisedRoutesCmd(cli_opts).run(
            prefix, opts.prefix_type, opts.json, opts.detail
        )

    @show.command("pre-area-policy")
    @click.argument("area", type=str)
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def pre_area_policy(
        cli_opts: bunch.Bunch, area: str, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        Show pre-policy routes for advertisment of specified area
        but after applying origination, if applicable
        """

        opts = cli_opts.advertised_routes_options
        prefix_mgr.AreaAdvertisedRoutesCmd(cli_opts).run(
            area,
            ctrl_types.RouteFilterType.PREFILTER_ADVERTISED,
            prefix,
            opts.prefix_type,
            opts.json,
            opts.detail,
        )

    @show.command("post-area-policy")
    @click.argument("area", type=str)
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def post_area_policy(
        cli_opts: bunch.Bunch, area: str, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        Show post-policy routes that are advertisment to specified area
        """

        opts = cli_opts.advertised_routes_options
        prefix_mgr.AreaAdvertisedRoutesCmd(cli_opts).run(
            area,
            ctrl_types.RouteFilterType.POSTFILTER_ADVERTISED,
            prefix,
            opts.prefix_type,
            opts.json,
            opts.detail,
        )

    @show.command("rejected-on-area")
    @click.argument("area", type=str)
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def rejected_on_area(
        cli_opts: bunch.Bunch, area: str, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        Show routes rejected by area policy on advertisement
        """

        opts = cli_opts.advertised_routes_options
        prefix_mgr.AreaAdvertisedRoutesCmd(cli_opts).run(
            area,
            ctrl_types.RouteFilterType.REJECTED_ON_ADVERTISE,
            prefix,
            opts.prefix_type,
            opts.json,
            opts.detail,
        )

    @show.command("pre-policy")
    @click.argument("area", type=str)
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def pre_policy(
        cli_opts: bunch.Bunch, area: str, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        DEPRECATED. use pre-area-policy
        """
        click.secho("pre-policy is deprecated, use pre-area-policy", fg="red")

    @show.command("post-policy")
    @click.argument("area", type=str)
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def post_policy(
        cli_opts: bunch.Bunch, area: str, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        DEPRECATED. use post-area-policy
        """
        click.secho("post-policy is deprecated, use post-area-policy", fg="red")

    @show.command("rejected")
    @click.argument("area", type=str)
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def rejected(
        cli_opts: bunch.Bunch, area: str, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        DEPRECATED. use rejected_on_area
        """
        click.secho("rejected is deprecated, use rejected-on-area", fg="red")

    @show.command("pre-origination-policy")
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def pre_origination_policy(
        cli_opts: bunch.Bunch, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        Show pre-origination-policy routes.
        Note: Only displays routes that came with an origination policy.
        """

        opts = cli_opts.advertised_routes_options
        prefix_mgr.AdvertisedRoutesWithOriginationPolicyCmd(cli_opts).run(
            ctrl_types.RouteFilterType.PREFILTER_ADVERTISED,
            prefix,
            opts.prefix_type,
            opts.json,
            opts.detail,
        )

    @show.command("post-origination-policy")
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def post_origination_policy(
        cli_opts: bunch.Bunch, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        Show post-policy routes that are accepted by origination policy. Only
        displays routes that came with an origination policy
        """

        opts = cli_opts.advertised_routes_options
        prefix_mgr.AdvertisedRoutesWithOriginationPolicyCmd(cli_opts).run(
            ctrl_types.RouteFilterType.POSTFILTER_ADVERTISED,
            prefix,
            opts.prefix_type,
            opts.json,
            opts.detail,
        )

    @show.command("rejected-on-origination")
    @click.argument("prefix", nargs=-1, type=str, required=False)
    @click.pass_obj
    def rejected_on_origination(
        cli_opts: bunch.Bunch, prefix: List[str]  # noqa: B902
    ) -> None:
        """
        Show routes rejected by origination policy
        """

        opts = cli_opts.advertised_routes_options
        prefix_mgr.AdvertisedRoutesWithOriginationPolicyCmd(cli_opts).run(
            ctrl_types.RouteFilterType.REJECTED_ON_ADVERTISE,
            prefix,
            opts.prefix_type,
            opts.json,
            opts.detail,
        )


class OriginatedRoutesCli(object):
    @click.command("originated-routes")
    @click.option(
        "--detail/--no-detail",
        default=False,
        help="Show all details including tags and area-stack",
    )
    @click.option(
        "--tag2name/--no-tag2name",
        default=False,
        help="Translate tag string to human readable name",
    )
    @click.pass_obj
    def show(
        cli_opts: bunch.Bunch,  # noqa: B902
        detail: bool,
        tag2name: bool,
    ) -> None:
        """
        Show originated routes configured on this node. Will show all by default
        """

        prefix_mgr.OriginatedRoutesCmd(cli_opts).run(detail, tag2name)


class PrefixMgrValidateCli(object):
    @click.command()
    @click.pass_obj
    def validate(cli_opts):
        """Runs validation checks on prefix manager module"""

        prefix_mgr.ValidateCmd(cli_opts).run()
