import milo
import discord
import re
import tempfile
import os
import logging
from discord.ext import commands
from dotenv import load_dotenv


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    await bot.tree.sync()
    logger.info("Bot is ready and commands are synced.")


@bot.tree.command(name="math", description="Solve a math problem")
async def hello(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=False)
    logger.info(f"Received math command from {interaction.user} with query: {query}")

    try:
        python_code, modified_response, last_boxed_sentence, last_var_value = (
            milo.solution_pipeline(query=query)
        )

        pattern = r"\\boxed\{([^\}]+)\}"
        new_text = re.sub(pattern, f"{last_var_value}", last_boxed_sentence, count=1)

        answer = f"### Answer:\n{new_text}\n\n### Step-by-step solution:\n{modified_response}\n```python\n{python_code}```"
        reply = f"### Query:\n{query}\n\n{answer}"

        if len(reply) <= 2000:
            await interaction.followup.send(reply)
            logging.info(f"Successfully sent the response to {interaction.user}")
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".md", encoding="utf-8"
            ) as temp_file:
                temp_file.write(reply)
                temp_file_path = temp_file.name

            with open(temp_file_path, "rb") as file:
                await interaction.followup.send(
                    file=discord.File(file, filename="response.md")
                )
                logging.info(
                    f"Successfully sent a Markdown file attachment to {interaction.user}"
                )

            os.remove(temp_file_path)

    except Exception as e:
        error_message = f"An error occurred while processing your request: {str(e)}"
        await interaction.followup.send(error_message)
        logger.error(f"Error processing math command for {interaction.user}: {str(e)}")


bot.run(BOT_TOKEN)
