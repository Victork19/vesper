from ..memory.models import Constitution
class Guardian:
    def __init__(self, memory): self.memory=memory
    def guard(self, action, risk, force_do_nothing=False):
        if force_do_nothing or risk>=9:return True,'The risk constitution requires doing nothing at this risk level.'
        if action.lower() in ('buy','sell','execute') and risk>=8:return True,'The risk constitution blocks high-risk action without stronger evidence.'
        return False,''
