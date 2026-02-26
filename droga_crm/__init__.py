# -*- coding: utf-8 -*-

from . import controllers
from . import models,reports,wizards


def create_days(env):
    day_model = env["droga.crm.settings.day"].sudo()
    existing_days = set(day_model.search([]).mapped("day"))
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Firday", "Saturday"]:
        if day not in existing_days:
            day_model.create({"day": day})
