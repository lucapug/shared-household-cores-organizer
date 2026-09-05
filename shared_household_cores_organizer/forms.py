from django import forms

from .models import Chore, Member


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ["name"]


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ["name"]
