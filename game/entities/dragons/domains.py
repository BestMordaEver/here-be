"""Dragon domain configurations."""
from dataclasses import dataclass


@dataclass  
class DragonDomainConfig:
    """Configuration for a dragon domain type."""
    color: str
    scorches_land: bool = False


# Domain configurations
DRAGON_DOMAINS = {
    'aquatic': DragonDomainConfig(color='#004080'),
    'mountain': DragonDomainConfig(color='#808080'),
    'verdant': DragonDomainConfig(color='#008000'),
    'scorched': DragonDomainConfig(color='#800000', scorches_land=True),
}

DEFAULT_DOMAIN = DragonDomainConfig(color='#808080')


def get_dragon_domain(properties: list) -> tuple[str, DragonDomainConfig]:
    """Get dragon domain name and config from properties list."""
    for domain_name, config in DRAGON_DOMAINS.items():
        if domain_name in properties:
            return domain_name, config
    return 'unknown', DEFAULT_DOMAIN
