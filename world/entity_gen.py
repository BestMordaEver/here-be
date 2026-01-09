from typing import TYPE_CHECKING, List, Set, Tuple
import random

from entities import Spirit, Village

if TYPE_CHECKING:
	from world import World


def find_resource_nodes(world: 'World') -> dict[str, List[List[Tuple[int, int]]]]:
	"""
	Find all interconnected resource nodes for each non-plains biome.
	Returns a dict mapping biome type to list of nodes (each node is a list of coordinates).
	"""
	visited: Set[Tuple[int, int]] = set()
	resource_nodes = {
		'water': [],
		'forest': [],
		'mountain': []
	}
	
	def flood_fill(start_x: int, start_y: int, biome: str) -> List[Tuple[int, int]]:
		"""Flood fill to find all connected tiles of the same biome."""
		stack = [(start_x, start_y)]
		node = []
		
		while stack:
			x, y = stack.pop()
			
			if (x, y) in visited:
				continue
			if x < 0 or x >= world.WIDTH or y < 0 or y >= world.HEIGHT:
				continue
			
			tile_biome = world.get_biome_from_height(world.height_map[y][x])
			if tile_biome != biome:
				continue
			
			visited.add((x, y))
			node.append((x, y))
			
			# Check 4-directional neighbors (not diagonal)
			for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
				stack.append((x + dx, y + dy))
		
		return node
	
	# Scan all tiles
	for y in range(world.HEIGHT):
		for x in range(world.WIDTH):
			if (x, y) in visited:
				continue
			
			biome = world.get_biome_from_height(world.height_map[y][x])
			
			# Only process non-plains biomes
			if biome in resource_nodes:
				node = flood_fill(x, y, biome)
				if node:
					resource_nodes[biome].append(node)
	
	return resource_nodes

def generate_spirits(world: 'World') -> None:
	"""
	Generate spirits on resource nodes after heightmap is created.
	Water and mountain spirits spawn on nodes with >= 5 tiles.
	Forest spirits spawn on nodes with >= 10 tiles.
	Spirits spawn at the tile closest to all other tiles in their domain.
	"""
	resource_nodes = find_resource_nodes(world)
	
	# Define thresholds for spirit spawning
	spirit_thresholds = {
		'water': 5,
		'mountain': 5,
		'forest': 10
	}
	
	for biome, nodes in resource_nodes.items():
		threshold = spirit_thresholds[biome]
		
		for node in nodes:
			# Check if node is large enough
			if len(node) >= threshold:
				# Find the most central tile - one with minimum total distance to all others
				min_total_distance = float('inf')
				spawn_coord = node[0]
				
				for candidate in node:
					total_distance = 0
					for tile in node:
						# Manhattan distance
						distance = abs(candidate[0] - tile[0]) + abs(candidate[1] - tile[1])
						total_distance += distance
					
					if total_distance < min_total_distance:
						min_total_distance = total_distance
						spawn_coord = candidate
				
				# Create the spirit with life equal to node size
				spirit = Spirit(
					type=biome,
					coordinates=spawn_coord,
					life=len(node),
					domain_area=len(node),
					domain_tiles=node
				)
				
				world.add_entity(spirit)


def check_village_spawn_area(world: 'World', center_x: int, center_y: int) -> bool:
	"""
	Check if a 7x7 area around the given center is all plains biome and unoccupied.
	Village center will be at (center_x, center_y).
	Returns True if spawn is valid, False otherwise.
	"""
	# Check if 7x7 area is within bounds
	if center_x < 3 or center_x >= world.WIDTH - 3:
		return False
	if center_y < 3 or center_y >= world.HEIGHT - 3:
		return False
	
	# Check if entire 7x7 area is plains biome
	for dy in range(-3, 4):
		for dx in range(-3, 4):
			x, y = center_x + dx, center_y + dy
			height = world.height_map[y][x]
			biome = world.get_biome_from_height(height)
			if biome != 'field':  # 'field' is the plains biome
				return False
	
	# Check if any entity occupies this 7x7 area
	for dy in range(-3, 4):
		for dx in range(-3, 4):
			x, y = center_x + dx, center_y + dy
			# Check all entities
			for entity in world.entities:
				# For settlements, check if they occupy this tile
				if hasattr(entity, 'occupies'):
					if entity.occupies((x, y)):
						return False
				# For non-settlements, check coordinates directly
				elif entity.coordinates == (x, y):
					return False
	
	return True


def check_settlement_distance(world: 'World', x: int, y: int, min_distance: int = 20) -> bool:
	"""
	Check if the given coordinates are at least min_distance away from any settlement.
	Returns True if far enough from all settlements, False otherwise.
	"""
	for entity in world.entities:
		if hasattr(entity, 'settlement_type'):
			# Calculate Manhattan distance to settlement center
			ex, ey = entity.coordinates
			distance = abs(x - ex) + abs(y - ey)
			if distance < min_distance:
				return False
	return True


def generate_village_name() -> str:
	"""Generate a random village name."""
	prefixes = [
		"Green", "Oak", "River", "Stone", "Mill", "Pine", "Elm", "Willow",
		"Brook", "Lake", "Hill", "Meadow", "Spring", "Autumn", "Summer", "Winter",
		"North", "South", "East", "West", "New", "Old", "High", "Low"
	]
	suffixes = [
		"vale", "ton", "field", "shire", "haven", "bury", "ford", "wood",
		"side", "ridge", "dale", "view", "bridge", "hollow", "crest", "port"
	]
	
	return f"{random.choice(prefixes)}{random.choice(suffixes)}"


def attempt_spawn_village(world: 'World') -> bool:
	"""
	Attempt to spawn a single village at a random location.
	Returns True if successful, False if spawn failed.
	"""
	# Try up to 100 random locations
	for _ in range(100):
		x = random.randint(0, world.WIDTH - 1)
		y = random.randint(0, world.HEIGHT - 1)
		
		# Check if far enough from settlements
		if not check_settlement_distance(world, x, y, min_distance=20):
			continue
		
		# Check if 7x7 area is valid
		if not check_village_spawn_area(world, x, y):
			continue
		
		# Spawn successful - create village
		name = generate_village_name()
		village = Village(name, (x, y))
		world.add_entity(village)
		return True
	
	return False