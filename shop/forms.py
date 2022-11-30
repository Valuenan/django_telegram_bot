from django import forms

from users.models import Carts


class ImportGoodsForm(forms.Form):
    file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))