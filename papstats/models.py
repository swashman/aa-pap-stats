"""Models."""

# Django
from django.contrib.auth.models import User
from django.db import models

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo


class PapStats(models.Model):
    """A meta model for app permissions."""

    class Meta:
        """Meta definitions."""

        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access this app"),
            ("admin_access", "Can access admin"),
            ("fc_access", "Can access fc"),
            ("alliance_access", "Can access alliance"),
        )


class MonthlyFleetType(models.Model):
    name = models.CharField(max_length=100)
    source = models.CharField(max_length=10)  # 'Imp' or 'afat'
    month = models.IntegerField()
    year = models.IntegerField()

    class Meta:
        unique_together = ("name", "source", "month", "year")


class MonthlyCorpStats(models.Model):
    corporation_id = models.PositiveIntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    fleet_type = models.ForeignKey(MonthlyFleetType, on_delete=models.CASCADE)
    total_fats = models.PositiveIntegerField()

    class Meta:
        unique_together = ("corporation_id", "month", "year", "fleet_type")

    def get_corporation(self):

        return EveCorporationInfo.objects.get(corporation_id=self.corporation_id)


class MonthlyUserStats(models.Model):
    user_id = models.PositiveIntegerField()
    corporation_id = models.PositiveIntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    fleet_type = models.ForeignKey(MonthlyFleetType, on_delete=models.CASCADE)
    total_fats = models.PositiveIntegerField()

    class Meta:
        unique_together = ("user_id", "month", "year", "fleet_type")

    def get_user(self):

        return User.objects.get(pk=self.user_id)

    def get_corporation(self):

        return EveCorporationInfo.objects.get(pk=self.corporation_id)


class CSVColumnMapping(models.Model):
    column_name = models.CharField(max_length=100, unique=True)
    mapped_to = models.CharField(max_length=100, blank=True, null=True)


class IgnoredCSVColumns(models.Model):
    column_name = models.CharField(max_length=100)

    def __str__(self):
        return self.column_name


class MonthlyCreatorStats(models.Model):
    creator_id = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    fleet_type = models.ForeignKey(MonthlyFleetType, on_delete=models.CASCADE)
    total_created = models.IntegerField(default=0)

    class Meta:
        unique_together = (("creator_id", "month", "year", "fleet_type"),)

    def get_creator(self):

        return User.objects.get(pk=self.creator_id)


class UnknownAccount(models.Model):
    account_name = models.CharField(max_length=255, unique=True)
    user_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.account_name
