"""
Git Plugin for Bot Bot.

This plugin provides GitHub integration commands for repository management,
issue creation, and issue retrieval through the Bot Discord bot.
"""

from discord.ext import commands
from loguru import logger

from bot.core.base_cog import BaseCog
from bot.core.bot import Bot
from bot.core.checks import requires_command_permission
from bot.services.wrappers.github import GithubService
from bot.shared.config import CONFIG
from bot.ui.buttons import GithubButton
from bot.ui.embeds import EmbedCreator


class Git(BaseCog):
    """GitHub integration plugin for repository and issue management."""

    def __init__(self, bot: Bot) -> None:
        """Initialize the Git plugin.

        Parameters
        ----------
        bot : Bot
            The bot instance to initialize the plugin with.
        """
        super().__init__(bot)

        # Check if GitHub configuration is available
        if self.unload_if_missing_config(
            condition=not CONFIG.EXTERNAL_SERVICES.GITHUB_APP_ID,
            config_name="GitHub App ID",
        ):
            return

        self.github = GithubService()
        self.repo_url = CONFIG.EXTERNAL_SERVICES.GITHUB_REPO_URL

    @commands.hybrid_group(
        name="git",
        aliases=["g"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def git(self, ctx: commands.Context[Bot]) -> None:
        """
        Github related commands.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context object for the command.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help("git")

    @git.command(
        name="get_repo",
        aliases=["r"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def get_repo(self, ctx: commands.Context[Bot]) -> None:
        """
        Get repository information.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context object for the command.
        """
        try:
            repo = await self.github.get_repo()

            embed = EmbedCreator.create_embed(
                EmbedCreator.INFO,
                bot=self.bot,
                user_name=ctx.author.name,
                user_display_avatar=ctx.author.display_avatar.url,
                title="Bot",
                description="",
            )
            embed.add_field(name="Description", value=repo.description, inline=False)
            embed.add_field(name="Stars", value=repo.stargazers_count)
            embed.add_field(name="Forks", value=repo.forks_count)
            embed.add_field(name="Open Issues", value=repo.open_issues_count)

        except Exception as e:
            await ctx.send(f"Error fetching repository: {e}", ephemeral=True)
            logger.error(f"Error fetching repository: {e}")

        else:
            await ctx.send(embed=embed, view=GithubButton(repo.html_url))
            logger.info(f"{ctx.author} fetched repository information.")

    @git.command(
        name="create_issue",
        aliases=["ci"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def create_issue(
        self,
        ctx: commands.Context[Bot],
        title: str,
        body: str,
    ) -> None:
        """
        Create an issue.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context object for the command.
        title : str
            The title of the issue.
        body : str
            The body of the issue.
        """
        try:
            issue_body = f"{body}\n\nAuthor: {ctx.author}"
            created_issue = await self.github.create_issue(title, issue_body)

            embed = EmbedCreator.create_embed(
                EmbedCreator.SUCCESS,
                bot=self.bot,
                user_name=ctx.author.name,
                user_display_avatar=ctx.author.display_avatar.url,
                title="Issue Created",
                description="The issue has been created successfully.",
            )
            embed.add_field(
                name="Issue Number",
                value=created_issue.number,
                inline=False,
            )
            embed.add_field(name="Title", value=title, inline=False)
            embed.add_field(name="Body", value=issue_body, inline=False)

        except Exception as e:
            await ctx.send(f"Error creating issue: {e}", ephemeral=True)
            logger.error(f"Error creating issue: {e}")

        else:
            await ctx.send(embed=embed, view=GithubButton(created_issue.html_url))
            logger.success(f"{ctx.author} created an issue.")

    @git.command(
        name="get_issue",
        aliases=["gi", "issue", "i"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def get_issue(self, ctx: commands.Context[Bot], issue_number: int) -> None:
        """
        Get an issue by issue number.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context object for the command.
        issue_number : int
            The number of the issue to retrieve.
        """
        try:
            issue = await self.github.get_issue(issue_number)

            embed = EmbedCreator.create_embed(
                EmbedCreator.INFO,
                bot=self.bot,
                user_name=ctx.author.name,
                user_display_avatar=ctx.author.display_avatar.url,
                title=issue.title,
                description=str(issue.body) if issue.body is not None else "",
            )
            embed.add_field(name="State", value=issue.state, inline=False)
            embed.add_field(name="Number", value=issue.number, inline=False)
            embed.add_field(
                name="User",
                value=issue.user.login if issue.user else "Unknown",
                inline=False,
            )
            embed.add_field(name="Created At", value=issue.created_at, inline=False)
            embed.add_field(name="Updated At", value=issue.updated_at, inline=False)

        except Exception as e:
            await ctx.send(f"Error fetching issue: {e}", ephemeral=True)
            logger.error(f"Error fetching issue: {e}")

        else:
            await ctx.send(embed=embed, view=GithubButton(issue.html_url))
            logger.info(f"{ctx.author} fetched an issue.")


async def setup(bot: Bot) -> None:
    """Set up the git plugin.

    Parameters
    ----------
    bot : Bot
        The bot instance to add the cog to.
    """
    await bot.add_cog(Git(bot))
