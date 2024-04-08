import discord
import logging
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.all()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.messages = True

#### 길드커맨드 등록
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        # 여러 길드 ID를 리스트로 관리
        guild_ids = [
            1031560516340023336 #하윤이네
            ,1162346164142751824 #GE
            ,1160436926315233280 #대롤
            ]

        # 각 길드에 대해 명령어 동기화 수행
        for guild_id in guild_ids:
            try:
                guild = discord.Object(id=guild_id)
                await self.tree.sync(guild=guild)
                logging.info(f"Commands synced successfully for guild ID: {guild_id}")
            except discord.errors.Forbidden:
                logging.warning(f"Missing access to sync commands in guild ID: {guild_id}")
            except Exception as e:
                logging.error(f"An error occurred while syncing commands for guild ID: {guild_id}: {e}")

bot = MyBot()


#### 봇 로그온 알림
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    check_empty_channel.start()

#### 신고 커맨드
@bot.tree.command(name="report", description="Report a user")
async def report(interaction: discord.Interaction):
    modal = ReportModal()
    await interaction.response.send_modal(modal)

#### 신고모달 호충 버튼 생성
@bot.command(name='신고모달')
async def send_modal_button(ctx):
    # 버튼이 포함된 View 생성하며 사용자에게 메시지와 함께 send
    view = ModalButtonView()
    await ctx.send("명백한 규칙 위반과 충분한 근거 및 자료가 충분할 경우에만 눌러주세요.", view=view)

#### 신고모달 호출 버튼
class ModalButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # 타임아웃을 무제한으로 설정

    @discord.ui.button(label="신고", style=discord.ButtonStyle.danger, custom_id="report_modal_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReportModal()
        await interaction.response.send_modal(modal)


#### 인스턴트 채널
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.name.startswith('🔑'):
        guild = after.channel.guild
        base_name = after.channel.name[1:]
        existing_channels = [c.name for c in guild.channels if isinstance(c, discord.VoiceChannel)]
        new_channel_name = get_new_channel_name(existing_channels, base_name)
        category = after.channel.category
        new_channel = await guild.create_voice_channel(f'🍔{new_channel_name}', category=category)
        await member.move_to(new_channel)
#### 인스턴트 채널 이름
def get_new_channel_name(existing_channels, base_name):
    i = 1
    while f'🍔{base_name}{i}' in existing_channels:
        i += 1
    return f'{base_name}{i}'
#### 인스턴트 채널 반복
@tasks.loop(seconds=5)
async def check_empty_channel():
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            if channel.name.startswith('🍔') and not channel.members:
                await channel.delete()



#### 상담버튼
@bot.command()
async def 상담버튼(ctx):
    """Creates the report message with a button."""
    logging.info(f"'상담버튼' command invoked by {ctx.author.name} (ID: {ctx.author.id}) in {ctx.guild.name} (ID: {ctx.guild.id})")
    content = (
        "안녕하세요, 고객센터입니다.\n"
        "버튼을 누르시면 1:1 창구가 개설됩니다.\n\n"
    )
    await ctx.send(content, view=Counsel())

#### 상담기능
class Counsel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝작성", style=discord.ButtonStyle.primary, custom_id="report_btn")
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        channel_name = f"상담-{user.name}" # 채널 이름 정의
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if not existing_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
            await channel.send(f"{user.mention}, 상담 내용을 작성해주세요.\n\n1. 상담 주제: \n2. 내용: 자유 기재\n3. 관련 자료: 이미지 또는 링크, 첨부, 로그 등")

            channel_link = f"https://discord.com/channels/{guild.id}/{channel.id}"
            await interaction.response.send_message(f"{user.mention}, 상담 채널이 생성되었습니다. [여기를 클릭하여 상담 채널로 이동하세요]({channel_link})", ephemeral=True)
        else:
            channel_link = f"https://discord.com/channels/{guild.id}/{existing_channel.id}"
            await interaction.response.send_message(f"{user.mention}, 상담 채널이 이미 존재합니다. [여기를 클릭하여 상담 채널로 이동하세요]({channel_link})", ephemeral=True)


#### 신고 채널에서의 신고자, 관리자 처리용 버튼 뷰
#신고자측
class ReporterView(discord.ui.View):
    def __init__(self, reported_member, reporter, report_channel, message_id, description, *args, **kwargs):
        super().__init__(timeout=86400, *args, **kwargs)
        self.description = description
        self.reported_member = reported_member
        self.reporter = reporter
        self.report_channel = report_channel
        self.message_id = message_id  # 메시지 ID 저장

    # 제출 버튼
    @discord.ui.button(label="제출", style=discord.ButtonStyle.green)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        admin_view = AdminView(
            reported_member=self.reported_member, 
            reporter=self.reporter,  # reporter 인자를 추가하여 전달
            report_channel=self.report_channel, 
            description=self.description,
            message_id=self.message_id
        )
        await interaction.message.edit(view=admin_view)
        await interaction.response.send_message("신고가 접수되었습니다.\n24시간 이내 관리자의 검토가 진행됩니다.", ephemeral=True)

    # 보정 버튼
    @discord.ui.button(label="보정", style=discord.ButtonStyle.blurple)
    async def correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        # `self.message_id`를 사용하여 신고 메시지 객체를 가져옵니다.
        if self.message_id:
            report_message = await interaction.channel.fetch_message(self.message_id)
            # 메시지 내용에서 필요한 정보를 추출합니다.
            lines = report_message.content.split("\n\n-신고 내용-\n", 1)  # "-신고 내용-"을 기준으로 내용 분할
            if len(lines) > 1:  # "-신고 내용-" 이후의 내용이 존재하는 경우
                header, description = lines  # header는 신고자와 신고 대상 정보를 포함, description은 신고 내용
                reported_mention = header.split("\n")[1].split(": ")[1]
                user_id = reported_mention.strip("<@!>").replace(">", "")  # 멘션에서 ID 추출 + '>' 문자 제거
                reported_user = await interaction.guild.fetch_member(int(user_id))
                user_name = reported_user.display_name

                # 수정을 위한 ReportModal 인스턴스 생성 및 호출
                modal = ReportModal(user_name=user_name, user_id=user_id, description=description, message_id=self.message_id)
                await interaction.response.send_modal(modal)
            else:
                await interaction.response.send_message("오류: 신고 내용을 분석할 수 없습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("오류: 메시지 ID를 찾을 수 없습니다.", ephemeral=True)

    # 취소 버튼
    @discord.ui.button(label="취소", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 신고 채널을 삭제하는 로직을 구현하세요.
        await self.report_channel.delete(reason="신고 취소")
        await interaction.response.send_message("신고가 취소되었습니다.", ephemeral=True)

    #타임아웃
    async def on_timeout(self):
        # 신고 채널을 삭제하고 신고자에게 신고가 기각되었음을 알립니다.
        # 신고 채널 삭제
        await self.report_channel.delete(reason="신고 타임아웃으로 인한 자동 기각")

        # 신고자에게 DM으로 신고 기각 메시지 전송
        dm_channel = await self.reporter.create_dm()
        await dm_channel.send(
            f"신고가 자동 기각되었습니다.\n신고대상 : {self.reported_member.display_name}\n기각 사유 : 미제출로 인한 시간 초과."
        )


#열람기능
class ReadReportView(discord.ui.View):
    def __init__(self, reported_member, reporter, description, investigation_channel, *args, **kwargs):
        super().__init__(timeout=86400, *args, **kwargs)  # 타임아웃을 24시간으로 설정
        self.reporter = reporter
        self.reported_member = reported_member
        self.description = description
        self.investigation_channel = investigation_channel  # 조사 채널 객체

    async def reveal_report(self, timeout_triggered=False):
        # 중앙화된 열람 로직
        timeout_message = "**시간 초과로 열람이 강제되었습니다.**\n" if timeout_triggered else ""
        message_content = (
            f"{timeout_message}"
            f"**신고 내용이 열람되었습니다.**\n"
            f"24시간 동안 소명 기회가 주어집니다.\n\n"
            f"신고자: {self.reporter.mention}\n"
            f"신고 대상: {self.reported_member.mention}\n\n"
            f"-신고 내용-\n{self.description}"
        )
        await self.investigation_channel.send(message_content)

    @discord.ui.button(label="열람", style=discord.ButtonStyle.blurple, custom_id="read_report")
    async def read_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        # '열람' 버튼 클릭 시 신고 내용을 조사 채널에 게시
        await self.reveal_report()
        await interaction.response.send_message("신고 내용이 열람되었습니다.", ephemeral=True)

    async def on_timeout(self):
        # 타임아웃 발생 시 신고 내용을 조사 채널에 자동으로 게시
        await self.reveal_report(timeout_triggered=True)


# 관리자 버튼을 위한 View 클래스
class AdminView(discord.ui.View):
    def __init__(self, reported_member, report_channel, description, reporter, message_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_channel = report_channel
        self.message_id = message_id
        self.reporter = reporter
        self.reported_member = reported_member
        self.description = description


    @discord.ui.button(label="접수", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        channel_name = f"조사-{self.reported_member.name}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not existing_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                self.reported_member: discord.PermissionOverwrite(read_messages=True, send_messages=True, add_reactions=False, embed_links=False, attach_files=False),
            }
            investigation_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
            read_report_view = ReadReportView(
                reported_member=self.reported_member,
                reporter=self.reporter,
                description=self.description,
                investigation_channel=investigation_channel
            )
            await investigation_channel.send(
                f"{self.reported_member.mention}님에 대한 신고가 도착했습니다.",
                view=read_report_view
            )

            channel_link = f"https://discord.com/channels/{guild.id}/{investigation_channel.id}"
            await interaction.response.send_message(f"조사 채널이 생성되었으며, 신고 내용이 송달되었습니다. [채널로 이동하기]({channel_link})", ephemeral=True)
        else:
            channel_link = f"https://discord.com/channels/{guild.id}/{existing_channel.id}"
            await interaction.response.send_message(f"'{channel_name}' 채널이 이미 존재합니다. [채널로 이동하기]({channel_link})", ephemeral=True)


    # 보정 요청 버튼
    @discord.ui.button(label="보정 요청", style=discord.ButtonStyle.blurple)
    async def request_correction_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        correction_modal = CorrectionRequestModal()
        await interaction.response.send_modal(correction_modal)
        reporter_view = ReporterView(
            reported_member=self.reported_member,
            reporter=self.reporter,
            report_channel=self.report_channel,
            message_id=self.message_id,
            description=self.description
        )
        report_message = await self.report_channel.fetch_message(self.message_id)
        await report_message.edit(view=reporter_view)


    # 기각 버튼
    @discord.ui.button(label="기각", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 신고 기각 및 채널 삭제 로직을 구현하세요.
        await self.report_channel.delete(reason="신고 기각")
        await interaction.response.send_message("신고가 기각되었습니다.", ephemeral=True)

    #타임아웃
    async def on_timeout(self):
        print("버튼의 활성 시간이 만료되었습니다.")



# 보정 요청 모달
class CorrectionRequestModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(title="보정 요청", *args, **kwargs)

        self.add_item(discord.ui.TextInput(
            label="보정 요청 사유",
            placeholder="보정이 필요한 사항을 입력해주세요.",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=10,
            max_length=1024
        ))

    async def on_submit(self, interaction: discord.Interaction):
        correction_reason = self.children[0].value
        await interaction.response.send_message(f"보정 요청 사유\n{correction_reason}", ephemeral=False)

#### 신고 모달 기능
class ReportModal(discord.ui.Modal):
    def __init__(self, user_name: str = "", user_id: str = "", description: str = "", message_id: str = None, *args, **kwargs):
        super().__init__(title="Report User", *args, **kwargs)
        self.message_id = message_id  # 메시지 ID 저장

        self.add_item(discord.ui.TextInput(
            label="사용자 ID",
            placeholder="예시) 닉네임#0000 (태그가 없을 경우 미기재)",
            default=user_name,  # 기존 값으로 초기화
            required=True,
            max_length=100,
            style=discord.TextStyle.short
        ))

        self.add_item(discord.ui.TextInput(
            label="사용자 고유 식별자",
            placeholder="18자리의 숫자로 이루어진 고유식별 코드",
            default=user_id,  # 기존 값으로 초기화
            required=True,
            max_length=100,
            style=discord.TextStyle.short
        ))

        self.add_item(discord.ui.TextInput(
            label="무슨 일이 발생했나요?",
            placeholder="예시) 규칙 #0 위반 & 상세내용",
            default=description,  # 기존 값으로 초기화
            required=True,
            min_length=100,
            max_length=2000,
            style=discord.TextStyle.paragraph
        ))

    async def on_submit(self, interaction: discord.Interaction):
        user_name = self.children[0].value  # 사용자명 (닉네임)
        user_id = self.children[1].value  # 사용자 고유 식별자는 문자열로 처리
        description = self.children[2].value
        reporter = interaction.user

        # 사용자 고유 식별자(ID)를 사용하여 길드 내 멤버 검색
        reported_member = interaction.guild.get_member(int(user_id)) # 사용자 고유 식별자(ID)를 사용하여 길드 내 멤버 검색

        if reported_member:
            # 멤버가 존재하는 경우, 사용자명이 일치하는지 확인
            if reported_member.display_name == user_name or reported_member.name == user_name:
                # 사용자명과 ID가 매치하는 경우, 신고 처리 로직 계속
                # 여기에 신고 처리 로직을 구현합니다.
                await interaction.response.send_message(f"신고가 작성되었습니다: {reported_member.display_name}", ephemeral=True)
            else:
                # 사용자명과 ID가 매치하지 않는 경우
                await interaction.response.send_message("제공된 사용자명과 ID가 일치하지 않습니다.", ephemeral=True)
                return
        else:
            # 멤버를 찾지 못한 경우
            await interaction.response.send_message("해당 ID를 가진 사용자를 찾을 수 없습니다.", ephemeral=True)
            return  # 멤버가 없거나 정보가 일치하지 않으면 여기서 처리 중단

        # 멤버가 존재하는 경우, 신고 채널 처리 계속
        report_channel_name = f"신고-{reported_member.name}"
        report_channel = discord.utils.get(interaction.guild.text_channels, name=report_channel_name)


        # ReportModal 클래스 내 on_submit 메서드의 일부
        if not report_channel:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                reporter: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                reported_member: discord.PermissionOverwrite(read_messages=False),  # 수정: 신고 대상이 채널을 볼 수 없도록 변경
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            report_channel = await interaction.guild.create_text_channel(name=report_channel_name, overwrites=overwrites)



        if self.message_id:
            # 보정 작업: 기존 메시지를 수정
            report_message = await interaction.channel.fetch_message(self.message_id)
            await report_message.edit(
                content=f"신고자: {reporter.mention} \n신고 대상: {reported_member.mention} \n\n-신고 내용-\n{description}",
                view=ReporterView(reported_member, reporter, report_channel, self.message_id, description)
            )
            await interaction.followup.send("신고 내용이 수정되었습니다.", ephemeral=True)
        else:
            # 새 신고 제출: 메시지를 보내고 수정하여 View 추가
            sent_message = await report_channel.send(
                f"신고자: {reporter.mention} \n신고 대상: {reported_member.mention} \n\n-신고 내용-\n{description}"
            )
            message_id = sent_message.id
            view = ReporterView(reported_member, reporter, report_channel, message_id, description)
            channel_link = f"https://discord.com/channels/{interaction.guild.id}/{report_channel.id}"
            followup_message = f"신고가 접수되었습니다. [신고 채널로 이동하기]({channel_link})"
            await sent_message.edit(view=view)
            await interaction.followup.send(followup_message, ephemeral=True)





bot.run("")
