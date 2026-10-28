class Resource:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name', '')
        self.url = kwargs.get('url', '')
        self.description = kwargs.get('description', '')
        self.category_id = kwargs.get('category_id')
        self.icon = kwargs.get('icon', '🔗')
        self.open_type = kwargs.get('open_type', 'website')
        self.executable_path = kwargs.get('executable_path')
        self.created_at = kwargs.get('created_at')
