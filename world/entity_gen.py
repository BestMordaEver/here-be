from typing import TYPE_CHECKING, List, Set, Tuple

from entities import Spirit

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