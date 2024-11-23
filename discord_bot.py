import discord
from discord import app_commands
import aiohttp
import os
from datetime import datetime

class ScreenshotBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


client = ScreenshotBot()


@client.tree.command(name="recent", description="Show recent screenshots")
async def recent(interaction: discord.Interaction, count: int = 5):
    """Show recent screenshots uploaded to the app"""
    try:
        # Connect to your SQLite database
        with sqlite3.connect("screenshots.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
            """
                SELECT s.filename, s.discord_username, s.upload_date, 
                    g.name as group_name, GROUP_CONCAT(t.name) as tags
                FROM screenshots s
                LEFT JOIN screenshot_groups g ON s.group_id = g.id
                LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                LEFT JOIN tags t ON st.tag_id = t.id
                GROUP BY s.id
                ORDER BY s.upload_date DESC
                LIMIT ?
            """,
                (count,),
            )
            screenshots = cursor.fetchall()

        if not screenshots:
            await interaction.response.send_message("No screenshots found!")
            return

        embed = discord.Embed(
            title="Recent Screenshots",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )

        for screenshot in screenshots:
            tags = screenshot["tags"].split(",") if screenshot["tags"] else []
            tag_text = " ".join([f"#{tag}" for tag in tags]) if tags else "No tags"

            embed.add_field(
                name=f"By {screenshot['discord_username']}",
                value=f"📅 {screenshot['upload_date']}\n🏷️ {tag_text}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}")


@client.tree.command(name="search", description="Search screenshots by tag or username")
async def search(interaction: discord.Interaction, query: str):
    """Search screenshots by tag or username"""
    try:
        with sqlite3.connect("screenshots.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
            """
                SELECT DISTINCT s.filename, s.discord_username, s.upload_date, 
                        g.name as group_name, GROUP_CONCAT(t.name) as tags
                FROM screenshots s
                LEFT JOIN screenshot_groups g ON s.group_id = g.id
                LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                LEFT JOIN tags t ON st.tag_id = t.id
                WHERE LOWER(s.discord_username) LIKE LOWER(?)
                    OR EXISTS (
                        SELECT 1 FROM tags t2
                        JOIN screenshot_tags st2 ON t2.id = st2.tag_id
                        WHERE st2.screenshot_id = s.id
                        AND LOWER(t2.name) LIKE LOWER(?)
                    )    
                GROUP BY s.id
                ORDER BY s.upload_date DESC
                LIMIT 5
            """,
                (f"%{query}%", f"%{query}%"),
            )
            results = cursor.fetchall()

        if not results:
            await interaction.response.send_message(f"No results found for '{query}'")
            return

        embed = discord.Embed(
            title=f"Search Results for '{query}'",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        for result in results:
            tags = result["tags"].split(",") if result["tags"] else []
            tag_text = " ".join([f"#{tag}" for tag in tags]) if tags else "No tags"

            embed.add_field(
                name=f"By {result['discord_username']}",
                value=f"📅 {result['upload_date']}\n🏷️ {tag_text}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}")


@client.tree.command(name="stats", description="Show screenshot statistics")
async def stats(interaction: discord.Interaction):
    """Show statistics about uploaded screenshots"""
    try:
        with sqlite3.connect("screenshots.db") as conn:
            conn.row_factory = sqlite3.Row

            # Get total counts
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(DISTINCT s.id) as total_screenshots,
                    COUNT(DISTINCT s.discord_username) as total_users,
                    COUNT(DISTINCT t.id) as total_tags,
                    COUNT(DISTINCT g.id) as total_groups
                    FROM screenshots s
                    LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                    LEFT JOIN tags t ON st.tag_id = t.id
                    LEFT JOIN screenshot_groups g ON s.group_id = g.id
                """
            )
            counts = cursor.fetchone()

            # Get top users
            cursor = conn.execute(
            """
                SELECT discord_username, COUNT(*) as count
                FROM screenshots
                GROUP BY discord_username
                ORDER BY count DESC
                LIMIT 3
            """
            )
            top_users = cursor.fetchall()

            # Get top tags
            cursor = conn.execute(
            """
                SELECT t.name, COUNT(*) as count
                FROM tags t
                JOIN screenshot_tags st ON t.id = st.tag_id
                GROUP BY t.id
                ORDER BY count DESC
                LIMIT 3
            """
            )
            top_tags = cursor.fetchall()

        embed = discord.Embed(
            title="Screenshot Statistics",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow(),
        )

        # Add overall stats
        embed.add_field(
            name="Overall Stats",
            value=f"📸 Total Screenshots: {counts['total_screenshots']}\n"
            f"👥 Total Users: {counts['total_users']}\n"
            f"🏷️ Total Tags: {counts['total_tags']}\n"
            f"📁 Total Groups: {counts['total_groups']}",
            inline=False,
        )

        # Add top users
        top_users_text = "\n".join(
            [
                f"#{i+1} {user['discord_username']}: {user['count']}"
                for i, user in enumerate(top_users)
            ]
        )
        embed.add_field(
            name="Top Contributors", value=top_users_text or "No data", inline=True
        )

        # Add top tags
        top_tags_text = "\n".join(
            [f"#{i+1} {tag['name']}: {tag['count']}" for i, tag in enumerate(top_tags)]
        )
        embed.add_field(name="Top Tags", value=top_tags_text or "No data", inline=True)

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}")
