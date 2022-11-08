from django.db import models
from zen_queries import QueriesDisabledError


class Alpha(models.Model):
    number = models.IntegerField()

    def value(self):
        return self.number + sum(b.value() for b in self.bravos.all())

    def __str__(self):
        return f"{self.number}"


class Bravo(models.Model):
    alpha: Alpha = models.ForeignKey(
        Alpha,
        on_delete=models.CASCADE,
        related_name="bravos",
    )

    number = models.IntegerField()

    def value(self):
        return self.number + sum(c.value() for c in self.charlies.all())

    def __str__(self):
        return f"{self.number}"


class Charlie(models.Model):
    bravo: Bravo = models.ForeignKey(
        Bravo,
        on_delete=models.CASCADE,
        related_name="charlies",
    )

    number = models.IntegerField()

    def value(self):
        try:
            return self.number + self.delta.value()
        except QueriesDisabledError as e:
            return 0

    def __str__(self):
        return f"{self.number}"


class Delta(models.Model):
    alpha: Alpha = models.OneToOneField(
        Alpha,
        on_delete=models.CASCADE,
        related_name="delta",
    )

    charlie: Charlie = models.OneToOneField(
        Charlie,
        on_delete=models.CASCADE,
        related_name="delta",
    )

    number = models.IntegerField()

    def value(self):
        return (
            self.number + sum(e.number for e in self.echoes.all()) + self.foxtrot.number
        )

    def __str__(self):
        return f"{self.number}"


class Echo(models.Model):
    delta: Delta = models.ForeignKey(
        Delta,
        on_delete=models.CASCADE,
        related_name="echoes",
    )

    number = models.IntegerField()

    def __str__(self):
        return f"{self.number}"


class Foxtrot(models.Model):
    delta: Delta = models.OneToOneField(
        Delta,
        on_delete=models.CASCADE,
        related_name="foxtrot",
    )

    number = models.IntegerField()

    def __str__(self):
        return f"{self.number}"
