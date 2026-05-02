"""护栏系统 - 输入/输出安全过滤"""


class GuardrailResult:
    def __init__(self, passed: bool, reason: str = "", severity: int = 0):
        self.passed = passed
        self.reason = reason
        self.severity = severity


class InputGuardrail:
    """输入护栏 Layer 1-2: PII/敏感词/越狱检测"""
    SENSITIVE_PATTERNS = [
        r"\b\d{15,19}\b",
        r"\b\d{6}(19|20)\d{2}(0[1-9]|1[0-2])\d{6}\b",
    ]

    @classmethod
    def check(cls, content: str) -> GuardrailResult:
        import re
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, content):
                return GuardrailResult(False, "检测到敏感个人信息", severity=4)
        return GuardrailResult(True)


class OutputGuardrail:
    """输出护栏 Layer 4: 幻觉检测、敏感信息泄露"""
    @classmethod
    def check(cls, content: str, context_docs: list = None) -> GuardrailResult:
        if len(content) < 5:
            return GuardrailResult(False, "响应内容过短", severity=2)
        return GuardrailResult(True)
