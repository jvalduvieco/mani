from typing import Type, Optional, Callable, Iterable

from injector import Injector

from mani.domain.cqrs.bus.command_bus import CommandBus
from mani.domain.cqrs.bus.effect_handler import EffectHandler
from mani.domain.cqrs.bus.event_bus import EventBus
from mani.domain.cqrs.bus.state_management.commands import DeleteState
from mani.domain.cqrs.bus.state_management.condition import HandlerCondition
from mani.domain.cqrs.bus.state_management.effect_to_state_mapping import EffectToStateMapper
from mani.domain.cqrs.effects import Effect, Command, Event
from mani.domain.model.repository.repository import Repository


class NotInterested:
    pass


def build_asynchronous_state_managing_class_effect_handler(a_handler: Type[EffectHandler],
                                                           repository_type: Type[Repository],
                                                           state_mapper: Optional[EffectToStateMapper],
                                                           condition: Optional[HandlerCondition],
                                                           injector: Injector) -> Callable[[Effect], None]:
    command_bus = injector.get(CommandBus)
    event_bus = injector.get(EventBus)

    def handler(effect: Effect) -> None:
        if condition is not None and not condition(effect):
            return

        handler_instance = injector.create_object(a_handler)
        repository = injector.get(repository_type)
        if state_mapper is not None:
            states = state_mapper(effect, repository)
            if type(states) == NotInterested:
                return
            if not isinstance(states, Iterable):
                states = [states]

            for previous_state in states:
                state, effects = handler_instance.handle(previous_state, effect)
                if state is not None:
                    repository.save(state)
                for effect in effects:
                    if isinstance(effect, Command):
                        command_bus.handle(effect)
                    elif isinstance(effect, Event):
                        event_bus.handle(effect)
                    elif isinstance(effect, DeleteState):
                        repository.delete(effect.id)
        else:
            state, effects = handler_instance.handle(effect)

            if state is not None:
                repository.save(state)
            for effect in effects:
                if isinstance(effect, Command):
                    command_bus.handle(effect)
                elif isinstance(effect, Event):
                    event_bus.handle(effect)

    return handler
