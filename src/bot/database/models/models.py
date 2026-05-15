"""
Database Models for Bot Bot.

This module defines all the SQLModel-based database models used by the Bot Discord bot,
including models for guilds, moderation cases, snippets, reminders, levels, starboard,
and permission management.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    Float,
    Index,
    Integer,
)
from sqlalchemy import Enum as PgEnum
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from .base import BaseModel
from .enums import CaseType

# =============================================================================
# PERMISSION SYSTEM MODELS
# =============================================================================


# =============================================================================
# PERMISSION SYSTEM MODELS
# =============================================================================


class PermissionRank(BaseModel, table=True):
    """Permission ranks for role-based access control.

    Defines hierarchical permission ranks that can be assigned to roles,
    controlling access to bot commands and features.

    Attributes
    ----------
    id : int, optional
        Auto-generated primary key.
    rank : int
        Numeric permission rank (0-10, higher = more permissions).
    name : str
        Human-readable name for the permission rank.
    description : str, optional
        Optional description of the rank's purpose and permissions.
    """

    __tablename__ = "permission_ranks"  # type: ignore[assignment]

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        description="Auto-generated unique identifier",
    )
    rank: int = Field(
        sa_type=Integer,
        unique=True,
        description="Numeric permission level (0-10, higher = more permissions)",
    )
    name: str = Field(
        max_length=100,
        unique=True,
        description="Human-readable name for this rank (e.g., 'Moderator', 'Admin')",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional description explaining this rank's purpose and permissions",
    )

    # Relationship to permission assignments
    assignments = Relationship(
        sa_relationship=relationship(
            "PermissionAssignment",
            back_populates="permission_rank",
            cascade="all, delete-orphan",
            passive_deletes=True,
            lazy="noload",
        ),
    )

    __table_args__ = (
        CheckConstraint("rank >= 0 AND rank <= 10", name="check_rank_range"),
        CheckConstraint("length(name) > 0", name="check_rank_name_not_empty"),
        Index("idx_permission_ranks_rank", "rank"),
    )

    def __repr__(self) -> str:
        """Return string representation showing rank and name."""
        return f"<PermissionRank id={self.id} rank={self.rank} name={self.name!r}>"


class PermissionAssignment(BaseModel, table=True):
    """Assigns permission ranks to Discord roles.

    Maps Discord roles to permission ranks, granting all members with that role
    the associated permission level.

    Attributes
    ----------
    id : int, optional
        Auto-generated primary key.
    permission_rank_id : int
        ID of the permission rank being assigned.
    role_id : int
        Discord role ID receiving the permission rank.
    """

    __tablename__ = "permission_assignments"  # type: ignore[assignment]

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        description="Auto-generated unique identifier",
    )
    permission_rank_id: int = Field(
        foreign_key="permission_ranks.id",
        ondelete="CASCADE",
        sa_type=BigInteger,
        description="ID of the permission rank being assigned to the role",
    )
    role_id: int = Field(
        sa_type=BigInteger,
        unique=True,
        description="Discord role ID receiving this permission rank",
    )

    # Relationships
    permission_rank = Relationship(
        sa_relationship=relationship(
            "PermissionRank",
            back_populates="assignments",
            lazy="noload",
        ),
    )

    __table_args__ = (
        CheckConstraint("role_id > 0", name="check_assignment_role_id_valid"),
        Index("idx_permission_assignments_rank", "permission_rank_id"),
        Index("idx_permission_assignments_role", "role_id"),
    )

    def __repr__(self) -> str:
        """Return string representation showing role and rank assignment."""
        return f"<PermissionAssignment id={self.id} role={self.role_id} rank={self.permission_rank_id}>"


class PermissionCommand(BaseModel, table=True):
    """Assigns permission requirements to specific commands.

    Defines the minimum permission rank required for specific commands,
    overriding default permission requirements.

    Attributes
    ----------
    id : int, optional
        Auto-generated primary key.
    command_name : str
        Name of the command (unique).
    required_rank : int
        Minimum permission rank required (0-10).
    description : str, optional
        Optional description of the command.
    """

    __tablename__ = "permission_commands"  # type: ignore[assignment]

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        description="Auto-generated unique identifier",
    )
    command_name: str = Field(
        min_length=1,
        max_length=200,
        unique=True,
        description="Name of the command (e.g., 'ban', 'kick', 'warn')",
    )
    required_rank: int = Field(
        sa_type=Integer,
        description="Minimum permission rank required to use this command (0-10)",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional human-readable description of the command",
    )

    __table_args__ = (
        CheckConstraint(
            "required_rank >= 0 AND required_rank <= 10",
            name="check_required_rank_range",
        ),
        CheckConstraint(
            "length(command_name) > 0",
            name="check_command_name_not_empty",
        ),
        Index("idx_permission_commands_rank", "required_rank"),
    )

    def __repr__(self) -> str:
        """Return string representation showing command and rank requirement."""
        return f"<PermissionCommand id={self.id} cmd={self.command_name!r} rank={self.required_rank}>"


# =============================================================================
# MODERATION MODELS
# =============================================================================


class Case(BaseModel, table=True):
    """Moderation case records.

    Represents individual moderation actions taken against users,
    such as bans, kicks, timeouts, warnings, etc.

    Attributes
    ----------
    id : int
        Unique case identifier.
    case_status : bool
        Whether the case is valid or voided.
    case_processed : bool
        Whether expiration has been processed.
    case_type : CaseType
        Type of moderation action taken.
    case_reason : str
        Reason for the moderation action.
    case_moderator_id : int
        Discord user ID of the moderator who took action.
    case_user_id : int
        Discord user ID of the moderated user.
    case_user_roles : list[int]
        User's roles at the time of the case.
    case_number : int, optional
        Sequential case number.
    case_expires_at : datetime, optional
        When temporary action expires.
    case_metadata : dict, optional
        Additional case-specific metadata.
    mod_log_message_id : int, optional
        Discord message ID in mod log.
    """

    # case is a reserved word in postgres, so we need to use a custom table name
    __tablename__ = "cases"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        description="Auto-generated unique case ID",
    )
    case_status: bool = Field(
        default=True,
        description="Whether the case is valid (True) or invalid/voided (False)",
    )
    case_processed: bool = Field(
        default=False,
        description="Whether expiration/completion has been processed for temporary actions",
    )

    case_type: CaseType | None = Field(
        default=None,
        sa_column=Column(PgEnum(CaseType, name="case_type_enum"), nullable=True),
        description="Type of moderation action (ban, kick, warn, timeout, etc.)",
    )

    case_reason: str = Field(
        max_length=2000,
        description="Reason provided for this moderation action",
    )
    case_moderator_id: int = Field(
        sa_type=BigInteger,
        description="Discord user ID of the moderator who performed this action",
    )
    case_user_id: int = Field(
        sa_type=BigInteger,
        description="Discord user ID of the user being moderated",
    )
    case_user_roles: list[int] = Field(
        default_factory=list,
        sa_type=JSON,
        description="List of role IDs the user had at the time of the case",
    )
    case_number: int | None = Field(
        default=None,
        ge=1,
        unique=True,
        description="Sequential case number for easy reference",
    )
    case_expires_at: datetime | None = Field(
        default=None,
        description="Expiration timestamp for temporary actions (tempban, timeout, jail)",
    )
    case_metadata: dict[str, str] | None = Field(
        default=None,
        sa_type=JSON,
        description="Additional case-specific metadata and context",
    )

    mod_log_message_id: int | None = Field(
        default=None,
        sa_type=BigInteger,
        description="Discord message ID in mod log channel (allows editing case embeds)",
    )

    __table_args__ = (
        CheckConstraint("case_user_id > 0", name="check_case_user_id_valid"),
        CheckConstraint("case_moderator_id > 0", name="check_case_moderator_id_valid"),
        CheckConstraint(
            "case_number IS NULL OR case_number >= 1",
            name="check_case_number_positive",
        ),
        CheckConstraint(
            "mod_log_message_id IS NULL OR mod_log_message_id > 0",
            name="check_mod_msg_id_valid",
        ),
        Index("idx_case_user", "case_user_id"),
        Index("idx_case_moderator", "case_moderator_id"),
        Index("idx_case_type", "case_type"),
        Index("idx_case_status", "case_status"),
        Index("idx_case_expires_at", "case_expires_at"),
        Index("idx_case_number", "case_number"),
        Index("idx_case_processed", "case_processed"),
        # Partial index for unprocessed temporary cases needing attention
        Index(
            "idx_case_unprocessed_expiring",
            "case_expires_at",
            postgresql_where="case_processed = FALSE AND case_expires_at IS NOT NULL",
        ),
        # Composite partial index for expired tempban queries
        Index(
            "idx_case_expired_tempbans",
            "case_type",
            "case_status",
            "case_expires_at",
            postgresql_where="case_type = 'TEMPBAN' AND case_status = TRUE AND case_processed = FALSE AND case_expires_at IS NOT NULL",
        ),
        # Composite partial index for jail/unjail case lookups
        Index(
            "idx_case_jail_unjail",
            "case_user_id",
            "case_type",
            "id",
            postgresql_where="case_type IN ('JAIL', 'UNJAIL')",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation showing case number, type and target user."""
        return f"<Case id={self.id} num={self.case_number} type={self.case_type} user={self.case_user_id}>"


# =============================================================================
# CUSTOM COMMAND MODELS
# =============================================================================


class Snippet(BaseModel, table=True):
    """Custom command snippets.

    Represents user-defined text snippets that can be triggered by custom commands.

    Attributes
    ----------
    id : int, optional
        Auto-generated primary key.
    snippet_name : str
        Name of the snippet command (unique).
    snippet_content : str, optional
        Content/text of the snippet.
    snippet_user_id : int
        Discord user ID who created the snippet.
    uses : int
        Number of times this snippet has been used.
    locked : bool
        Whether the snippet is locked (prevents editing/deletion).
    alias : str, optional
        Optional alias name for the snippet.
    """

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        description="Auto-generated unique snippet ID",
    )
    snippet_name: str = Field(
        min_length=1,
        max_length=100,
        unique=True,
        description="Command name to trigger this snippet",
    )
    snippet_content: str | None = Field(
        default=None,
        max_length=4000,
        description="Text content returned when snippet is triggered",
    )
    snippet_user_id: int = Field(
        sa_type=BigInteger,
        description="Discord user ID of the snippet creator",
    )

    uses: int = Field(
        default=0,
        ge=0,
        sa_type=Integer,
        description="Usage count for tracking snippet popularity",
    )
    locked: bool = Field(
        default=False,
        description="Whether snippet is locked from editing/deletion",
    )
    alias: str | None = Field(
        default=None,
        max_length=100,
        description="Optional alternative name for triggering the snippet",
    )

    __table_args__ = (
        CheckConstraint("snippet_user_id > 0", name="check_snippet_user_id_valid"),
        CheckConstraint("uses >= 0", name="check_snippet_uses_positive"),
        CheckConstraint(
            "length(snippet_name) > 0",
            name="check_snippet_name_not_empty",
        ),
        Index("idx_snippet_user", "snippet_user_id"),
        Index("idx_snippet_name", "snippet_name", unique=True),
        Index("idx_snippet_uses", "uses"),
        Index("idx_snippet_locked", "locked"),
    )

    def __repr__(self) -> str:
        """Return string representation showing ID and name."""
        return f"<Snippet id={self.id} name={self.snippet_name!r}>"


# =============================================================================
# UTILITY MODELS
# =============================================================================


class Reminder(BaseModel, table=True):
    """Scheduled reminders for users.

    Represents reminders that users can set to be notified about at a specific time.

    Attributes
    ----------
    id : int, optional
        Auto-generated primary key.
    reminder_content : str
        Content of the reminder message.
    reminder_expires_at : datetime
        When the reminder should trigger.
    reminder_channel_id : int
        Channel ID where reminder should be sent.
    reminder_user_id : int
        Discord user ID who set the reminder.
    reminder_sent : bool
        Whether the reminder has been sent.
    """

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        description="Auto-generated unique reminder ID",
    )
    reminder_content: str = Field(
        max_length=2000,
        description="Message content to send when reminder triggers",
    )
    reminder_expires_at: datetime = Field(
        description="Timestamp when the reminder should trigger",
    )
    reminder_channel_id: int = Field(
        sa_type=BigInteger,
        description="Discord channel ID where reminder notification will be sent",
    )
    reminder_user_id: int = Field(
        sa_type=BigInteger,
        description="Discord user ID who created the reminder",
    )
    reminder_sent: bool = Field(
        default=False,
        description="Whether the reminder notification has been delivered",
    )

    __table_args__ = (
        CheckConstraint("reminder_user_id > 0", name="check_reminder_user_id_valid"),
        CheckConstraint(
            "reminder_channel_id > 0",
            name="check_reminder_channel_id_valid",
        ),
        Index("idx_reminder_expires_at", "reminder_expires_at"),
        Index("idx_reminder_user", "reminder_user_id"),
        Index("idx_reminder_sent", "reminder_sent"),
        # Partial index for pending reminders that need to be sent
        Index(
            "idx_reminder_pending",
            "reminder_expires_at",
            postgresql_where="reminder_sent = FALSE",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation showing user and expiration."""
        return f"<Reminder id={self.id} user={self.reminder_user_id} expires={self.reminder_expires_at:%Y-%m-%d %H:%M}>"


class AFK(BaseModel, table=True):
    """Away From Keyboard status for users.

    Tracks when users set themselves as AFK and provides a reason
    for their absence.

    Attributes
    ----------
    member_id : int
        Discord user ID (primary key).
    nickname : str
        User's nickname when they went AFK.
    reason : str
        Reason for being AFK.
    since : datetime
        When the user went AFK.
    until : datetime, optional
        When the AFK status expires (for scheduled AFK).
    enforced : bool
        Whether AFK is enforced (user can't remove it themselves).
    perm_afk : bool
        Whether this is a permanent AFK status.
    """

    member_id: int = Field(
        primary_key=True,
        sa_type=BigInteger,
        description="Discord user ID",
    )
    nickname: str = Field(
        min_length=1,
        max_length=100,
        description="User's display name when they went AFK",
    )
    reason: str = Field(
        min_length=1,
        max_length=500,
        description="Reason provided for being AFK",
    )
    since: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="Timestamp when user went AFK",
    )
    until: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp for scheduled AFK",
    )
    enforced: bool = Field(
        default=False,
        description="Whether AFK is enforced by mods (user can't self-remove)",
    )
    perm_afk: bool = Field(
        default=False,
        description="Whether this is a permanent AFK status",
    )

    __table_args__ = (
        CheckConstraint("member_id > 0", name="check_afk_member_id_valid"),
        CheckConstraint(
            "until IS NULL OR until > since",
            name="check_afk_until_after_since",
        ),
        Index("idx_afk_member", "member_id"),
        Index("idx_afk_enforced", "enforced"),
        Index("idx_afk_perm", "perm_afk"),
        Index("idx_afk_until", "until"),
        # Partial index for temporary (expiring) AFK statuses
        Index(
            "idx_afk_expiring",
            "until",
            postgresql_where="until IS NOT NULL AND perm_afk = FALSE",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation showing user."""
        return f"<AFK member={self.member_id} since={self.since}>"


# =============================================================================
# PROGRESSION MODELS
# =============================================================================


class Levels(BaseModel, table=True):
    """User experience and leveling data.

    Tracks user experience points and level progression.

    Attributes
    ----------
    member_id : int
        Discord user ID (primary key).
    xp : float
        Experience points accumulated by the user.
    level : int
        Current level derived from XP.
    blacklisted : bool
        Whether user is blacklisted from gaining XP.
    last_message : datetime
        Timestamp of last message for XP cooldown.
    """

    member_id: int = Field(
        primary_key=True,
        sa_type=BigInteger,
        description="Discord user ID",
    )
    xp: float = Field(
        default=0.0,
        ge=0.0,
        sa_type=Float,
        description="Experience points accumulated by the user",
    )
    level: int = Field(
        default=0,
        ge=0,
        sa_type=Integer,
        description="Current level calculated from XP",
    )
    blacklisted: bool = Field(
        default=False,
        description="Whether user is prevented from gaining XP",
    )
    last_message: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="Timestamp of last message for XP gain cooldown",
    )

    __table_args__ = (
        CheckConstraint("member_id > 0", name="check_levels_member_id_valid"),
        CheckConstraint("xp >= 0", name="check_xp_positive"),
        CheckConstraint("level >= 0", name="check_level_positive"),
        Index("idx_levels_member", "member_id"),
        Index("idx_levels_xp", "xp"),
        Index("idx_levels_level", "level"),
        Index("idx_levels_blacklisted", "blacklisted"),
        Index("idx_levels_last_message", "last_message"),
    )

    def __repr__(self) -> str:
        """Return string representation showing member, level and XP."""
        return f"<Levels member={self.member_id} lvl={self.level} xp={self.xp:.1f}>"


# =============================================================================
# FEATURE MODELS
# =============================================================================


class Starboard(BaseModel, table=True):
    """Starboard configuration.

    Defines the starboard channel and emoji settings for highlighting
    messages that receive enough reactions.

    Attributes
    ----------
    id : int
        Config ID (primary key, single row).
    starboard_channel_id : int
        Discord channel ID where starred messages are posted.
    starboard_emoji : str
        Emoji used for starring messages.
    starboard_threshold : int
        Number of reactions needed to appear on starboard.
    """

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_type=BigInteger,
        description="Primary key (single-row configuration)",
    )
    starboard_channel_id: int = Field(
        sa_type=BigInteger,
        description="Channel ID where starred messages will be posted",
    )
    starboard_emoji: str = Field(
        max_length=64,
        description="Emoji (unicode or custom) used for starring messages",
    )
    starboard_threshold: int = Field(
        default=1,
        ge=1,
        sa_type=Integer,
        description="Number of reactions required for message to appear on starboard",
    )

    __table_args__ = (
        CheckConstraint(
            "starboard_channel_id > 0",
            name="check_starboard_channel_id_valid",
        ),
        CheckConstraint(
            "starboard_threshold >= 1",
            name="check_starboard_threshold_positive",
        ),
        Index("idx_starboard_channel", "starboard_channel_id"),
        Index("idx_starboard_threshold", "starboard_threshold"),
    )

    def __repr__(self) -> str:
        """Return string representation showing channel and threshold."""
        return f"<Starboard channel={self.starboard_channel_id} threshold={self.starboard_threshold}>"


class StarboardMessage(BaseModel, table=True):
    """Messages that have been starred on the starboard.

    Tracks individual messages that have been posted to the starboard
    along with their star counts and original message information.

    Attributes
    ----------
    id : int
        Original Discord message ID (primary key).
    message_content : str
        Content of the original message.
    message_expires_at : datetime
        When the starboard entry expires.
    message_channel_id : int
        Original channel ID where message was posted.
    message_user_id : int
        Discord user ID of the message author.
    star_count : int
        Current number of star reactions.
    starboard_message_id : int
        ID of the starboard message in the starboard channel.
    """

    __tablename__ = "starboard_message"  # pyright: ignore[reportAssignmentType]

    id: int = Field(
        primary_key=True,
        sa_type=BigInteger,
        description="Original Discord message ID",
    )
    message_content: str = Field(
        max_length=4000,
        description="Text content of the original message",
    )
    message_expires_at: datetime = Field(
        description="When this starboard entry should be removed",
    )
    message_channel_id: int = Field(
        sa_type=BigInteger,
        description="Channel ID where the original message was posted",
    )
    message_user_id: int = Field(
        sa_type=BigInteger,
        description="Discord user ID of the message author",
    )
    star_count: int = Field(
        default=0,
        ge=0,
        sa_type=Integer,
        description="Current number of star reactions on the message",
    )
    starboard_message_id: int = Field(
        sa_type=BigInteger,
        description="Discord message ID of the starboard post in the starboard channel",
    )

    __table_args__ = (
        CheckConstraint("id > 0", name="check_starboard_msg_id_valid"),
        CheckConstraint(
            "message_channel_id > 0",
            name="check_starboard_msg_channel_id_valid",
        ),
        CheckConstraint(
            "message_user_id > 0",
            name="check_starboard_msg_user_id_valid",
        ),
        CheckConstraint(
            "starboard_message_id > 0",
            name="check_starboard_post_id_valid",
        ),
        CheckConstraint("star_count >= 0", name="check_star_count_positive"),
        Index("idx_starboard_msg_expires", "message_expires_at"),
        Index("idx_starboard_msg_user", "message_user_id"),
        Index("idx_starboard_msg_channel", "message_channel_id"),
        Index("idx_starboard_msg_star_count", "star_count"),
    )

    def __repr__(self) -> str:
        """Return string representation showing original message and user."""
        return f"<StarboardMessage id={self.id} user={self.message_user_id} channel={self.message_channel_id}>"
