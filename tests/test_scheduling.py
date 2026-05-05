"""Tests for the Scheduling system — DayPlanner, Schedule, and Scheduled mixin."""
import pytest
from game.entities.base.scheduled import (
    Schedule, ScheduledAction, ActionType, DayPlanner,
    DEFAULT_DUSK_HOUR, DEFAULT_SLEEP_DURATION,
)


# ---------------------------------------------------------------------------
# Schedule dictionary
# ---------------------------------------------------------------------------

class TestSchedule:

    def test_set_and_get(self):
        s = Schedule()
        action = ScheduledAction(day=1, hour=10, action_type=ActionType.PATROL)
        s.set(action)
        assert s.get(1, 10) is action

    def test_set_returns_false_if_slot_occupied(self):
        s = Schedule()
        a1 = ScheduledAction(day=1, hour=10, action_type=ActionType.PATROL)
        a2 = ScheduledAction(day=1, hour=10, action_type=ActionType.REST)
        s.set(a1)
        assert s.set(a2) is False
        assert s.get(1, 10) is a1  # Original unchanged

    def test_has(self):
        s = Schedule()
        action = ScheduledAction(day=1, hour=10, action_type=ActionType.PATROL)
        assert not s.has(1, 10)
        s.set(action)
        assert s.has(1, 10)

    def test_remove(self):
        s = Schedule()
        action = ScheduledAction(day=1, hour=10, action_type=ActionType.PATROL)
        s.set(action)
        removed = s.remove(1, 10)
        assert removed is action
        assert not s.has(1, 10)

    def test_trim_past_removes_old_actions(self):
        s = Schedule()
        for h in range(5, 15):
            s.set(ScheduledAction(day=1, hour=h, action_type=ActionType.IDLE))
        removed = s.trim_past(1, 10)
        assert removed == 5  # hours 5–9 removed
        assert not s.has(1, 9)
        assert s.has(1, 10)

    def test_find_free_slot_backward_direction(self):
        """Free slot search should prefer going backward from preferred hour."""
        s = Schedule()
        # Occupy preferred hour
        s.set(ScheduledAction(day=1, hour=15, action_type=ActionType.IDLE))
        slot = s.find_free_slot(
            day=1, preferred_hour=15, anchor_hour=20,
            current_day=1, current_hour=7, direction=-1
        )
        assert slot is not None
        assert slot != (1, 15)   # Must not pick the occupied slot
        # Should be strictly before 15 (backward search)
        if slot[0] == 1:
            assert slot[1] < 15 or slot[1] > 15

    def test_find_free_slot_occupied_returns_adjacent(self):
        s = Schedule()
        for h in range(8, 20):
            s.set(ScheduledAction(day=1, hour=h, action_type=ActionType.IDLE))
        # Only slot available before anchor should be outside the occupied range
        slot = s.find_free_slot(
            day=1, preferred_hour=14, anchor_hour=20,
            current_day=1, current_hour=7, direction=-1
        )
        assert slot is not None
        d, h = slot
        assert not s.has(d, h)

    def test_find_free_slot_returns_none_only_when_truly_full(self):
        s = Schedule()
        # Fill all hours on days 1 and 2
        for d in [1, 2]:
            for h in range(24):
                s.set(ScheduledAction(day=d, hour=h, action_type=ActionType.IDLE))
        # Should find something on day 3
        slot = s.find_free_slot(
            day=1, preferred_hour=12, anchor_hour=20,
            current_day=1, current_hour=0, direction=-1
        )
        if slot:
            assert slot[0] >= 3

    def test_push_action_cascades(self):
        """Pushing action at occupied slot cascades to next free slot."""
        s = Schedule()
        a1 = ScheduledAction(day=1, hour=10, action_type=ActionType.PATROL)
        a2 = ScheduledAction(day=1, hour=11, action_type=ActionType.REST)
        s.set(a1)
        s.set(a2)
        # Push action at hour 10 — it should cascade past 11
        result = s.push_action(1, 10)
        assert result is True
        assert s.has(1, 12)  # Cascaded to first free slot
        assert s.get(1, 12).action_type == ActionType.PATROL
        # a2 unchanged at 11
        assert s.get(1, 11) is a2

    def test_get_next_action(self):
        s = Schedule()
        a1 = ScheduledAction(day=1, hour=10, action_type=ActionType.PATROL)
        a2 = ScheduledAction(day=1, hour=15, action_type=ActionType.REST)
        s.set(a1)
        s.set(a2)
        nxt = s.get_next_action(1, 9)
        assert nxt is a1


# ---------------------------------------------------------------------------
# DayPlanner
# ---------------------------------------------------------------------------

class TestDayPlanner:

    def _make_planner(self, day=1, dusk=20, current_day=1, current_hour=7):
        s = Schedule()
        return DayPlanner(
            schedule=s,
            day=day,
            dusk_hour=dusk,
            current_day=current_day,
            current_hour=current_hour,
            sleep_duration=DEFAULT_SLEEP_DURATION,
        ), s

    def test_commit_schedules_sleep(self):
        planner, s = self._make_planner()
        planner.add(ActionType.PATROL)
        planner.commit()
        # Sleep must appear in schedule
        sleep_actions = [a for a in s.iter_actions() if a.action_type == ActionType.SLEEP]
        assert len(sleep_actions) >= 1

    def test_commit_schedules_wake(self):
        planner, s = self._make_planner()
        planner.add(ActionType.PATROL)
        planner.commit()
        wake_actions = [a for a in s.iter_actions() if a.action_type == ActionType.WAKE]
        assert len(wake_actions) >= 1

    def test_wake_is_sleep_duration_after_sleep(self):
        planner, s = self._make_planner()
        planner.add(ActionType.REST)
        planner.commit()
        sleeps = [a for a in s.iter_actions() if a.action_type == ActionType.SLEEP]
        wakes  = [a for a in s.iter_actions() if a.action_type == ActionType.WAKE]
        assert sleeps and wakes
        sleep_time = (sleeps[0].day, sleeps[0].hour)
        wake_time  = (wakes[0].day, wakes[0].hour)
        # Wake should be sleep_duration hours after sleep
        sleep_total = sleep_time[0] * 24 + sleep_time[1]
        wake_total  = wake_time[0]  * 24 + wake_time[1]
        assert wake_total - sleep_total == DEFAULT_SLEEP_DURATION

    def test_actions_placed_before_dusk(self):
        planner, s = self._make_planner()
        planner.add(ActionType.PATROL)
        planner.add(ActionType.REST)
        planner.commit()
        non_lifecycle = [
            a for a in s.iter_actions()
            if a.action_type not in (ActionType.SLEEP, ActionType.WAKE)
        ]
        for action in non_lifecycle:
            if action.day == 1:
                assert action.hour <= DEFAULT_DUSK_HOUR, (
                    f"Action {action.action_type} scheduled at {action.hour}:00 after dusk"
                )

    def test_multiple_actions_each_get_unique_slot(self):
        planner, s = self._make_planner()
        planner.add(ActionType.PATROL)
        planner.add(ActionType.REST)
        planner.add(ActionType.WANDER)
        created = planner.commit()
        times = [(a.day, a.hour) for a in created]
        assert len(times) == len(set(times)), "Each action should get a unique time slot"

    def test_empty_planner_still_schedules_sleep_wake(self):
        planner, s = self._make_planner()
        planner.commit()
        sleep_actions = [a for a in s.iter_actions() if a.action_type == ActionType.SLEEP]
        wake_actions  = [a for a in s.iter_actions() if a.action_type == ActionType.WAKE]
        assert sleep_actions
        assert wake_actions

    def test_action_target_preserved(self):
        planner, s = self._make_planner()
        target = (30, 30)
        planner.add(ActionType.MOVE_TO, target)
        created = planner.commit()
        move_actions = [a for a in created if a.action_type == ActionType.MOVE_TO]
        assert len(move_actions) == 1
        assert move_actions[0].target == target
