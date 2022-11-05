from django.db import models


class Alpha(models.Model):
    number = models.IntegerField()

    def value(self):
        self.bravo: Bravo
        return self.number - 1 / self.bravo.value()


class Bravo(models.Model):
    alpha: Alpha = models.OneToOneField(
        Alpha,
        on_delete=models.CASCADE,
        related_name="bravo",
    )

    number = models.IntegerField()

    def value(self):
        self.charlie: Charlie
        return self.number ** self.charlie.value()


class Charlie(models.Model):
    bravo: Bravo = models.OneToOneField(
        Bravo,
        on_delete=models.CASCADE,
        related_name="charlie",
    )

    number = models.IntegerField()

    def value(self):
        self.delta: Delta
        return self.number / self.delta.value()


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
        echoes: list[Echo] = list(self.echoes.all())
        self.foxtrot: Foxtrot
        return self.number * sum(e.number for e in echoes) + self.foxtrot.number


class Echo(models.Model):
    delta: Delta = models.ForeignKey(
        Delta,
        on_delete=models.CASCADE,
        related_name="echoes",
    )

    number = models.IntegerField()


class Foxtrot(models.Model):
    delta: Delta = models.OneToOneField(
        Delta,
        on_delete=models.CASCADE,
        related_name="foxtrot",
    )

    number = models.IntegerField()
