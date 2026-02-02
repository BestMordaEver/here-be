from typing import TYPE_CHECKING, List, Set, Tuple
import random
import math

from game.entities import Spirit, Village, Settlement

if TYPE_CHECKING:
	from . import World


# Spirit generation constants
WATER_SPIRIT_THRESHOLD = 5  # Minimum tiles for water spirit
MOUNTAIN_SPIRIT_THRESHOLD = 5  # Minimum tiles for mountain spirit
FOREST_SPIRIT_THRESHOLD = 10  # Minimum tiles for forest spirit
FOREST_MAX_DISTANCE = 25  # Max distance before forest node splits
KMEANS_ITERATIONS = 10  # K-means clustering iterations

# Village/City spawn constants
VILLAGE_MIN_SETTLEMENT_DISTANCE = 20  # Min distance between settlements for village
CITY_MIN_SETTLEMENT_DISTANCE = 30  # Min distance between settlements for city
CITY_SPAWN_ATTEMPTS = 50  # Attempts to find valid city location
CATTLE_SPAWN_ATTEMPTS = 10  # Attempts to find valid cattle location

# City starting blessings
CITY_STARTING_BLESSINGS = 10  # Enough to spawn spire immediately


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


def _split_forest_node(node: List[Tuple[int, int]], max_distance: float = FOREST_MAX_DISTANCE) -> List[List[Tuple[int, int]]]:
	"""
	Split a forest node into multiple sub-nodes if the maximum Euclidean distance exceeds threshold.
	Uses k-means clustering to partition the forest into roughly equal parts.
	"""
	# Calculate maximum Euclidean distance between any two points
	max_dist = 0
	for i, p1 in enumerate(node):
		for p2 in node[i+1:]:
			dist = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
			if dist > max_dist:
				max_dist = dist
	
	# If max distance is within threshold, no split needed
	if max_dist <= max_distance:
		return [node]
	
	# Determine number of clusters based on max distance
	num_clusters = max(2, int(max_dist / max_distance) + 1)
	
	# Simple k-means clustering
	# Initialize centroids randomly from existing points
	centroids = random.sample(node, min(num_clusters, len(node)))
	
	for iteration in range(KMEANS_ITERATIONS):  # iterations should converge
		# Assign each point to nearest centroid
		clusters = [[] for _ in range(len(centroids))]
		for point in node:
			min_dist = float('inf')
			closest_cluster = 0
			for i, centroid in enumerate(centroids):
				dist = math.sqrt((point[0] - centroid[0])**2 + (point[1] - centroid[1])**2)
				if dist < min_dist:
					min_dist = dist
					closest_cluster = i
			clusters[closest_cluster].append(point)
		
		# Update centroids to be the point closest to cluster average
		new_centroids = []
		for cluster in clusters:
			if cluster:
				avg_x = sum(p[0] for p in cluster) / len(cluster)
				avg_y = sum(p[1] for p in cluster) / len(cluster)
				# Find the point in the cluster closest to the average
				min_dist = float('inf')
				closest_point = cluster[0]
				for point in cluster:
					dist = math.sqrt((point[0] - avg_x)**2 + (point[1] - avg_y)**2)
					if dist < min_dist:
						min_dist = dist
						closest_point = point
				new_centroids.append(closest_point)
		
		centroids = new_centroids
	
	# Post-process: ensure each cluster is a single connected component
	# If a cluster has disconnected regions, split them into separate clusters
	final_clusters = []
	for cluster in clusters:
		if cluster:
			connected_components = _split_into_connected_components(cluster)
			final_clusters.extend(connected_components)
	
	# Return non-empty clusters
	return [cluster for cluster in final_clusters if cluster]


def _split_into_connected_components(tiles: List[Tuple[int, int]]) -> List[List[Tuple[int, int]]]:
	"""
	Split a list of tiles into connected components.
	Two tiles are connected if they are 4-directionally adjacent.
	"""
	if not tiles:
		return []
	
	tile_set = set(tiles)
	visited = set()
	components = []
	
	def flood_fill_component(start: Tuple[int, int]) -> List[Tuple[int, int]]:
		"""Find all tiles connected to start tile."""
		stack = [start]
		component = []
		
		while stack:
			tile = stack.pop()
			
			if tile in visited or tile not in tile_set:
				continue
			
			visited.add(tile)
			component.append(tile)
			
			# Check 4-directional neighbors
			x, y = tile
			for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
				neighbor = (x + dx, y + dy)
				if neighbor in tile_set and neighbor not in visited:
					stack.append(neighbor)
		
		return component
	
	# Find all connected components
	for tile in tiles:
		if tile not in visited:
			component = flood_fill_component(tile)
			if component:
				components.append(component)
	
	return components


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
		'water': WATER_SPIRIT_THRESHOLD,
		'mountain': MOUNTAIN_SPIRIT_THRESHOLD,
		'forest': FOREST_SPIRIT_THRESHOLD
	}
	
	for biome, nodes in resource_nodes.items():
		threshold = spirit_thresholds[biome]
		
		for node in nodes:
			# Check if node is large enough
			if len(node) >= threshold:
				# For forests, check if we need to split based on distance
				sub_nodes = [node]
				if biome == 'forest':
					sub_nodes = _split_forest_node(node, max_distance=FOREST_MAX_DISTANCE)
				
				# Create spirits for each sub-node (or the original node if not split)
				for sub_node in sub_nodes:
					# Skip if sub-node is too small after splitting
					if len(sub_node) < threshold:
						continue
					
					# Find the most central tile - one with minimum total distance to all others
					min_total_distance = float('inf')
					spawn_coord = sub_node[0]
					
					for candidate in sub_node:
						total_distance = 0
						for tile in sub_node:
							# Manhattan distance
							distance = abs(candidate[0] - tile[0]) + abs(candidate[1] - tile[1])
							total_distance += distance
						
						if total_distance < min_total_distance:
							min_total_distance = total_distance
							spawn_coord = candidate
					
					# Create the spirit with its domain tiles
					spirit = Spirit(
						type=biome,
						coordinates=spawn_coord,
						domain_tiles=sub_node
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
	for dy in range(-3, 3):
		for dx in range(-3, 3):
			x, y = center_x + dx, center_y + dy
			height = world.height_map[y][x]
			biome = world.get_biome_from_height(height)
			if biome != 'field':  # 'field' is the plains biome
				return False
	
	# Check if any entity occupies this 7x7 area
	for dy in range(-3, 3):
		for dx in range(-3, 3):
			x, y = center_x + dx, center_y + dy
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


def attempt_spawn_village(world: 'World') -> bool:
	"""
	Attempt to spawn a single village at a random location.
	Returns True if successful, False if spawn failed.
	"""

	x = random.randint(0, world.WIDTH - 1)
	y = random.randint(0, world.HEIGHT - 1)
	
	# Check if far enough from settlements
	if not check_settlement_distance(world, x, y, min_distance=VILLAGE_MIN_SETTLEMENT_DISTANCE):
		return False
	
	# Check if 7x7 area is valid
	if not check_village_spawn_area(world, x, y):
		return False
	
	# Spawn successful - create village
	name = generate_village_name()
	village = Village(name, (x, y))
	world.add_entity(village)
	return True


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
		if world.get_biome_from_height(height) != 'field':
			continue
		
		# Check no entity at location
		if world.get_entities_at((x, y)):
			continue
		
		# Spawn cattle
		color = random.choice(CATTLE_COLORS)
		cattle = Cattle(color, (x, y), life=30)
		world.add_entity(cattle)
		return True
	
	return False


def check_city_spawn_area(world: 'World', center_x: int, center_y: int) -> bool:
	"""
	Check if an 11x11 area around the given center is all plains biome.
	City center will be at (center_x, center_y). City is 5x5 so we need extra margin.
	Returns True if spawn is valid, False otherwise.
	"""
	# Check if 11x11 area is within bounds
	if center_x < 5 or center_x >= world.WIDTH - 5:
		return False
	if center_y < 5 or center_y >= world.HEIGHT - 5:
		return False
	
	# Check if entire 11x11 area is plains biome
	for dy in range(-5, 6):
		for dx in range(-5, 6):
			x, y = center_x + dx, center_y + dy
			height = world.height_map[y][x]
			biome = world.get_biome_from_height(height)
			if biome != 'field':
				return False
	
	return True


def attempt_spawn_city(world: 'World') -> bool:
	"""Spawn the initial city at a random location.
	This is the first settlement, so no proximity checks needed.
	City starts with resources to immediately spawn a spire and send worker caravans.
	Returns True if successful, False if spawn failed.
	"""
	from game.entities import City
	
	# Try multiple times to find a valid location
	for _ in range(CITY_SPAWN_ATTEMPTS):
		x = random.randint(0, world.WIDTH - 1)
		y = random.randint(0, world.HEIGHT - 1)
		
		# Check if 11x11 area is valid plains
		if not check_city_spawn_area(world, x, y):
			continue
		
		# Spawn successful - create city with starting blessings
		name = generate_village_name()  # Use same name generator
		city = City(name, (x, y))		
		city.blessings = CITY_STARTING_BLESSINGS
		
		world.add_entity(city)
		return True
	
	return False