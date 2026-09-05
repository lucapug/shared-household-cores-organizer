from django.db import models
from django.utils import timezone


class HouseholdConfig(models.Model):
    anchor_date = models.DateField()

    def __str__(self):
        return f"Anchor: {self.anchor_date}"

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(anchor_date=timezone.localdate())
        return obj


class Member(models.Model):
    name = models.CharField(max_length=100)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.name


class Chore(models.Model):
    name = models.CharField(max_length=200)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.name


class ChoreWeekState(models.Model):
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="week_states")
    week_start = models.DateField()
    done = models.BooleanField(default=False)
    note = models.TextField(blank=True, default="")
    covered_by = models.ForeignKey(
        Member,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="covered_week_states",
    )

    class Meta:
        ordering = ["week_start", "chore__position", "chore__id"]
        constraints = [
            models.UniqueConstraint(fields=["chore", "week_start"], name="unique_chore_per_week")
        ]

    def __str__(self):
        return f"{self.chore.name} @ {self.week_start}"
