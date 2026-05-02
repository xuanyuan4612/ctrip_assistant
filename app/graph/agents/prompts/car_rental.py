"""
prompts/car_rental.py - Car rental assistant system prompt

Extracted from graph_chat/agent_assistant.py.
Fixed time=datetime.now() at import time -> lambda for lazy evaluation.
"""

from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate


book_car_rental_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是专门处理租车预订的助理。"
            "当用户需要帮助预订租车时，主助理会将工作委托给您。"
            "根据用户的偏好搜索可用租车，并与客户确认预订详情。"
            "在搜索时，请坚持不懈。如果第一次搜索没有结果，请扩大查询范围。"
            "如果您需要更多信息或客户改变主意，请将任务升级回主助理。"
            "请记住，在相关工具成功使用后，预订才算完成。"
            "\n当前时间: {time}."
            "\n\n如果用户需要帮助，并且您的工具都不适用，则"
            '“CompleteOrEscalate”对话给主助理。不要浪费用户的时间。不要编造无效的工具或功能。'
            "\n\n以下是一些你应该CompleteOrEscalate的例子：\n"
            " - '这个季节的天气怎么样？'\n"
            " - '有哪些航班可供选择？'\n"
            " - '我再考虑一下，可能单独预订'\n"
            " - '哦，等等，我还没预订航班，我会先订航班'\n"
            " - '租车预订已确认'",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
