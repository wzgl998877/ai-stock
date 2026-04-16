from fastapi import HTTPException


class AppException(HTTPException):
    """应用异常基类"""

    def __init__(self, status_code: int, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


class InvalidInputError(AppException):
    def __init__(self, message: str = "输入参数无效"):
        super().__init__(status_code=400, code="INVALID_INPUT", message=message)


class RateLimitedError(AppException):
    def __init__(self, message: str = "分析正在进行中，请稍候"):
        super().__init__(status_code=429, code="RATE_LIMITED", message=message)


class AIServiceError(AppException):
    def __init__(self, message: str = "AI服务暂时不可用，请稍后重试"):
        super().__init__(status_code=503, code="AI_SERVICE_ERROR", message=message)


class NoIndustryTagError(AppException):
    def __init__(self, message: str = "请至少保留1个行业，或选择「未分类」"):
        super().__init__(status_code=400, code="NO_INDUSTRY_TAG", message=message)


class EmptyContentError(AppException):
    def __init__(self, message: str = "分析内容不能为空"):
        super().__init__(status_code=400, code="EMPTY_CONTENT", message=message)


class DuplicateTitleError(AppException):
    def __init__(self, message: str = "已有同名提醒，是否继续添加？"):
        super().__init__(status_code=409, code="DUPLICATE_TITLE", message=message)
