class Category:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name', '')
        self.icon = kwargs.get('icon', '📁')
