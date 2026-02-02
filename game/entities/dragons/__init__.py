"""Dragon type and domain configurations."""
from .types import DRAGON_TYPES, DragonTypeConfig, get_dragon_type, DEFAULT_TYPE
from .domains import DRAGON_DOMAINS, DragonDomainConfig, get_dragon_domain, DEFAULT_DOMAIN

__all__ = [
    'DRAGON_TYPES', 'DragonTypeConfig', 'get_dragon_type', 'DEFAULT_TYPE',
    'DRAGON_DOMAINS', 'DragonDomainConfig', 'get_dragon_domain', 'DEFAULT_DOMAIN',
]
