from typing import TYPE_CHECKING, List, Set, Tuple
import random
import math

from game.entities import Spirit, Village, Settlement
from game.world.types import Biome

if TYPE_CHECKING:
	from . import World
	from game.entities.settlement.city import City


# Spirit generation constants
LAKE_SPIRIT_THRESHOLD = 5  # Minimum tiles for lake spirit
MOUNTAIN_SPIRIT_THRESHOLD = 5  # Minimum tiles for mountain spirit
FOREST_SPIRIT_THRESHOLD = 10  # Minimum tiles for forest spirit
FOREST_MAX_DISTANCE = 25  # Max distance before forest node splits
KMEANS_ITERATIONS = 10  # K-means clustering iterations

# Village/City spawn constants
VILLAGE_MIN_SETTLEMENT_DISTANCE = 20  # Min distance between settlements for village
CITY_MIN_SETTLEMENT_DISTANCE = 30  # Min distance between settlements for city
SETTLEMENT_SPAWN_ATTEMPTS = 50  # Attempts to find valid city location
CATTLE_SPAWN_ATTEMPTS = 10  # Attempts to find valid cattle location


def generate_spirits(world: 'World') -> None:
	"""
	Generate spirits on resource nodes after heightmap is created.
	Water and mountain spirits spawn on nodes with >= 5 tiles.
	Forest spirits spawn on nodes with >= 10 tiles.
	Spirits spawn at the tile closest to all other tiles in their domain.
	"""
	# Map each resource biome to its spirit type and minimum tile threshold
	from game.entities.spirit import SpiritType
	biome_spirit_map = {
		Biome.WATER:    (SpiritType.LAKE,     LAKE_SPIRIT_THRESHOLD),
		Biome.FOREST:   (SpiritType.FOREST,   FOREST_SPIRIT_THRESHOLD),
		Biome.MOUNTAIN: (SpiritType.MOUNTAIN, MOUNTAIN_SPIRIT_THRESHOLD),
	}

	# --- Flood-fill: find all connected resource nodes ---
	visited: Set[Tuple[int, int]] = set()
	resource_nodes: dict[Biome, List[List[Tuple[int, int]]]] = {
		Biome.WATER: [],
		Biome.FOREST: [],
		Biome.MOUNTAIN: [],
	}

	for y in range(world.HEIGHT):
		for x in range(world.WIDTH):
			if (x, y) in visited:
				continue

			biome = world.get_biome_from_height(world.height_map[y][x])
			if biome not in resource_nodes:
				continue

			# Flood fill to collect the connected component
			stack = [(x, y)]
			node: List[Tuple[int, int]] = []

			while stack:
				cx, cy = stack.pop()

				if (cx, cy) in visited:
					continue
				if cx < 0 or cx >= world.WIDTH or cy < 0 or cy >= world.HEIGHT:
					continue
				if world.get_biome_from_height(world.height_map[cy][cx]) != biome:
					continue

				visited.add((cx, cy))
				node.append((cx, cy))

				for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
					stack.append((cx + dx, cy + dy))

			if node:
				resource_nodes[biome].append(node)

	# --- Process each biome's nodes and spawn spirits ---
	for biome, nodes in resource_nodes.items():
		spirit_type, threshold = biome_spirit_map[biome]

		for node in nodes:
			if len(node) < threshold:
				continue

			# For forests, split oversized nodes into smaller clusters
			sub_nodes = [node]
			if biome == Biome.FOREST:
				max_dist = 0.0
				for i, p1 in enumerate(node):
					for p2 in node[i + 1:]:
						d = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
						if d > max_dist:
							max_dist = d

				if max_dist > FOREST_MAX_DISTANCE:
					# K-means clustering to partition the node
					num_clusters = max(2, int(max_dist / FOREST_MAX_DISTANCE) + 1)
					centroids = random.sample(node, min(num_clusters, len(node)))
					clusters: List[List[Tuple[int, int]]] = []

					for _ in range(KMEANS_ITERATIONS):
						clusters = [[] for _ in range(len(centroids))]
						for point in node:
							min_d = float('inf')
							closest = 0
							for i, centroid in enumerate(centroids):
								d = math.sqrt((point[0] - centroid[0]) ** 2 + (point[1] - centroid[1]) ** 2)
								if d < min_d:
									min_d = d
									closest = i
							clusters[closest].append(point)

						new_centroids = []
						for cluster in clusters:
							if cluster:
								avg_x = sum(p[0] for p in cluster) / len(cluster)
								avg_y = sum(p[1] for p in cluster) / len(cluster)
								min_d = float('inf')
								closest_point = cluster[0]
								for point in cluster:
									d = math.sqrt((point[0] - avg_x) ** 2 + (point[1] - avg_y) ** 2)
									if d < min_d:
										min_d = d
										closest_point = point
								new_centroids.append(closest_point)
						centroids = new_centroids

					# Ensure each cluster is a single connected component
					sub_nodes = []
					for cluster in clusters:
						if not cluster:
							continue
						tile_set = set(cluster)
						comp_visited: Set[Tuple[int, int]] = set()
						for start in cluster:
							if start in comp_visited:
								continue
							comp_stack = [start]
							component: List[Tuple[int, int]] = []
							while comp_stack:
								tile = comp_stack.pop()
								if tile in comp_visited or tile not in tile_set:
									continue
								comp_visited.add(tile)
								component.append(tile)
								tx, ty = tile
								for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
									neighbor = (tx + dx, ty + dy)
									if neighbor in tile_set and neighbor not in comp_visited:
										comp_stack.append(neighbor)
							if component:
								sub_nodes.append(component)

			for sub_node in sub_nodes:
				if len(sub_node) < threshold:
					continue

				# Find the most central tile (minimum total Manhattan distance to all others)
				min_total_distance = float('inf')
				spawn_coord = sub_node[0]
				for candidate in sub_node:
					total_distance = sum(
						abs(candidate[0] - tile[0]) + abs(candidate[1] - tile[1])
						for tile in sub_node
					)
					if total_distance < min_total_distance:
						min_total_distance = total_distance
						spawn_coord = candidate

				spirit = Spirit(
					world=world,
					type=spirit_type,
					coordinates=spawn_coord,
					domain_tiles=sub_node,
				)
				world.add_entity(spirit)


def check_settlement_spawn_area(world: 'World', center_x: int, center_y: int, margin: int) -> bool:
	"""
	Check if an area around the given center is all plains biome and unoccupied.
	The area size is (2*margin + 1) x (2*margin + 1).
	Returns True if spawn is valid, False otherwise.
	"""
	# Check if area is within bounds
	if center_x < margin or center_x >= world.WIDTH - margin:
		return False
	if center_y < margin or center_y >= world.HEIGHT - margin:
		return False
	
	# Check if entire area is plains biome and unoccupied
	for dy in range(-margin, margin + 1):
		for dx in range(-margin, margin + 1):
			x, y = center_x + dx, center_y + dy
			height = world.height_map[y][x]
			biome = world.get_biome_from_height(height)
			if biome != Biome.FIELD:
				return False
			if world.get_entities_at((x, y)):
				return False
	
	return True


def check_settlement_distance(world: 'World', x: int, y: int, min_distance: int = 20) -> bool:
	"""
	Check if the given coordinates are at least min_distance away from any settlement.
	Returns True if far enough from all settlements, False otherwise.
	"""
	for entity in world.entities:
		if issubclass(entity.__class__, Settlement):
			if entity.get_distance((x,y)) < min_distance:
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


def attempt_spawn_settlement(world: 'World', settlement_type: str = 'village') -> 'Settlement | None':
	"""
	Attempt to spawn a settlement at a random location.
	Returns the settlement if successful, None if spawn failed.
	
	Args:
		world: The world to spawn in
		settlement_type: 'village' or 'city'
	"""
	from game.entities import City, Village
	
	# Configuration based on settlement type
	if settlement_type == 'city':
		margin = 5  # 11x11 area
		min_distance = CITY_MIN_SETTLEMENT_DISTANCE
		settlement_class = City
	else:
		margin = 3  # 7x7 area
		min_distance = VILLAGE_MIN_SETTLEMENT_DISTANCE
		settlement_class = Village
	
	# Try multiple times to find a valid location
	for _ in range(SETTLEMENT_SPAWN_ATTEMPTS):
		x = random.randint(0, world.WIDTH - 1)
		y = random.randint(0, world.HEIGHT - 1)
		
		# Check if far enough from other settlements
		if not check_settlement_distance(world, x, y, min_distance=min_distance):
			continue
		
		# Check if area is valid plains
		if not check_settlement_spawn_area(world, x, y, margin):
			continue
		
		# Spawn successful - create settlement
		name = generate_village_name()
		settlement = settlement_class(world, name, (x, y))
		world.add_entity(settlement)
		return settlement
	
	return None


# Cattle spawning constants
CATTLE_MAX_COUNT = 20  # Maximum cattle in the world
CATTLE_COLORS = ["#8B4513", "#A0522D", "#D2691E", "#CD853F"]  # Brown shades


def attempt_spawn_cattle(world: 'World') -> bool:
	"""
	Attempt to spawn cattle at a random plains location.
	Returns True if successful, False if spawn failed.
	"""
	from game.entities import Cattle
	
	# Count existing cattle
	cattle_count = sum(1 for e in world.entities if e.__class__.__name__ == 'Cattle')
	if cattle_count >= CATTLE_MAX_COUNT:
		return False
	
	# Try to find a valid spawn location
	for _ in range(CATTLE_SPAWN_ATTEMPTS):
		x = random.randint(0, world.WIDTH - 1)
		y = random.randint(0, world.HEIGHT - 1)
		
		# Must be on plains
		height = world.height_map[y][x]
		if world.get_biome_from_height(height) != Biome.FIELD:
			continue
		
		# Check no entity at location
		if world.get_entities_at((x, y)):
			continue
		
		# Spawn cattle
		color = random.choice(CATTLE_COLORS)
		cattle = Cattle(world, color, (x, y))
		world.add_entity(cattle)
		return True
	
	return False


