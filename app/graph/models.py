"""LangGraph 子图路由与任务完成模型。

定义 Pydantic 模型，用于在主助理与各专业子助理之间路由控制权，
以及标记子任务的完成/升级状态。
"""

from pydantic import BaseModel, Field


class CompleteOrEscalate(BaseModel):
    """标记当前子任务为已完成，或将控制权升级回主助理。

    当子助理完成工作、用户改变主意、或需要主助理重新路由时使用。
    """

    cancel: bool = True
    reason: str

    class Config:
        json_schema_extra = {
            "example": {
                "cancel": True,
                "reason": "用户改变了对当前任务的想法。",
            },
            "example2": {
                "cancel": True,
                "reason": "我已经完成了任务。",
            },
            "example3": {
                "cancel": False,
                "reason": "我需要搜索用户的电子邮件或日历以获取更多信息。",
            },
        }


class ToFlightBookingAssistant(BaseModel):
    """路由控制权至航班预订子助理。

    该子助理专门处理航班的查询、预订、修改及取消。
    """

    request: str = Field(
        description="更新航班助理在继续之前需要澄清的任何后续问题。"
    )


class ToBookCarRental(BaseModel):
    """路由控制权至租车子助理。

    该子助理专门处理租车的查询与预订。
    """

    location: str = Field(description="用户想要租车的位置。")
    start_date: str = Field(description="租车开始日期。")
    end_date: str = Field(description="租车结束日期。")
    request: str = Field(
        description="用户关于租车的任何额外信息或请求。"
    )

    class Config:
        json_schema_extra = {
            "示例": {
                "location": "巴塞尔",
                "start_date": "2023-07-01",
                "end_date": "2023-07-05",
                "request": "我需要一辆带自动变速器的小型车。",
            }
        }


class ToHotelBookingAssistant(BaseModel):
    """路由控制权至酒店预订子助理。

    该子助理专门处理酒店查询、预订及取消。
    """

    location: str = Field(description="用户想要预订酒店的位置。")
    checkin_date: str = Field(description="酒店入住日期。")
    checkout_date: str = Field(description="酒店退房日期。")
    request: str = Field(
        description="用户关于酒店预订的任何额外信息或请求。"
    )

    class Config:
        json_schema_extra = {
            "示例": {
                "location": "苏黎世",
                "checkin_date": "2023-08-15",
                "checkout_date": "2023-08-20",
                "request": "我偏好靠近市中心且房间有景观的酒店。",
            }
        }


class ToBookExcursion(BaseModel):
    """路由控制权至游览/旅行推荐子助理。

    该子助理专门处理目的地推荐及游览预订。
    """

    location: str = Field(
        description="用户想要预订推荐旅行的位置。"
    )
    request: str = Field(
        description="用户关于旅行推荐的任何额外信息或请求。"
    )

    class Config:
        json_schema_extra = {
            "示例": {
                "location": "卢塞恩",
                "request": "用户对户外活动和风景名胜感兴趣。",
            }
        }
