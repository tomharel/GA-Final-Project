<?php
	
	require_once ('db_config.php');
	
	function get_rating($raw_rating, $star_rating=FALSE) {
		// Outliers
		if ($raw_rating > 5) {
			$raw_rating = 5;
		}
		
		if ($raw_rating < 0) {
			$raw_rating = 0;
		}
		
		if ($star_rating) {
			$rating =  round((2.0 * $raw_rating), 0) / 2;
		} else {
			$rating = number_format($raw_rating, 2);
		}
		
		return $rating;
	}
	
	
	
	// START SCRIPT
	global $connection;	
	
	// Rec table
	$table = 'recommendations2';
	if (isset($_REQUEST['rec_table'])) {
		$table = $_REQUEST['rec_table'];
	}
	
	$rand = FALSE;
	if (!isset($_REQUEST['client_id']) || $_REQUEST['client_id'] == 'rand') {
		$rand = TRUE;	
		$sql = "SELECT client_id FROM clients ORDER BY RAND() LIMIT 1";
		$query = mysqli_query($connection, $sql);
		if ($zz = mysqli_fetch_assoc($query)) {
			$client_id = $zz['client_id'];
		}
	} else {
		$client_id = $_REQUEST['client_id'];
	}
	
	// LIMIT ITEMS TO RETURN
	$limit = 25;
	if (isset($_REQUEST['limit'])) {
		$limit = $_REQUEST['limit'];
	}
	
	// MAP ZOOM
	$zoom = 13;
	
	// GET LAT/LNG FROM DB
	$sql = "SELECT lat, lng FROM clients WHERE client_id = {$client_id} LIMIT 1";
	$query = mysqli_query($connection, $sql);
	if ($z = mysqli_fetch_assoc($query)) {
		$lat = $z['lat'];
		$lng = $z['lng'];
	} else {
		if ($client_id == 0) {
			$lat = 37.759396;
			$lng = -122.445153;
			$zoom = 12;
		} else {
			die("Client ID not found");
		}
		
	}
		
	$info = "'{$client_id}', {$lat}, {$lng}";
	
	// GET REC DATA FROM DB
	$params = '';
	if ($limit) {
		$params .= " LIMIT {$limit}";
	}
	
	$sql = "SELECT r.item_id, r.rating, i.restaurant_name, i.item_name, i.img FROM recommendations r INNER JOIN items i ON (r.item_id = i.item_id)  WHERE client_id = {$client_id} {$params}";
	$query = mysqli_query($connection, $sql);
	$results = array();
	while ($z = mysqli_fetch_assoc($query)) {
		$results[] = $z;
	}
		
	
?>

<!DOCTYPE html>
<html> 
<head> 
  <meta http-equiv="content-type" content="text/html; charset=UTF-8" /> 
  <title>Google Maps Multiple Markers</title>
  <link rel="stylesheet" type="text/css" href="css\table.css">
  <script src="http://maps.google.com/maps/api/js?sensor=false"></script>
  <script src="http://ajax.aspnetcdn.com/ajax/jQuery/jquery-1.10.1.min.js"></script>
</head> 
<body style="text-align: center;">
	
  <h1>Recommendations for Client ID: <?php echo $client_id; ?></h1>	
  <div id="map" style="width: 800px; height: 300px; margin: auto; border: 1px solid;"></div>
	
	
<?php if (isset($results) && !empty($results)) { ?>
<div style="width: 800px; margin: auto;">
	<h3 style="text-align: left; margin-bottom: 5px;">Recommended Items (<?php echo count($results); ?>):</h3>
	<table class="CSSTableGenerator">
		<thead>
			<th>#</th>
			<th>Item ID</th>
			<th>Rating</th>
			<th>Item Name</th>
			<th>Restaurant Name</th>
			<th>Image</th>
		</thead>
		<tbody>
			
			<?php
				
				foreach ($results as $loc => $row) {
					$num = $loc + 1;
					$rating = get_rating($row['rating']);
					
					
					if(!empty($row['img'])) {
						$image_link = "http://www.eat24hours.com" . $row['img']; 
						$image = "<a href=\"{$image_link}\"><img height=75 width=75 src=\"{$image_link}\"></a>";
					} else {
						$image_link = 'img/no-thumb.png';
						$image = "<img height=75 width=75 src=\"{$image_link}\">";
					}
					
					print "<tr>";
						print "<td style=\"text-align: center\">{$num}</td>";
						print "<td style=\"text-align: center\">{$row['item_id']}</td>";
						print "<td style=\"text-align: center\">{$rating}</td>";
						print "<td>{$row['item_name']}</td>";
						print "<td>{$row['restaurant_name']}</td>";
						print "<td style='text-align: center;'>{$image}</td>";
						
					print "</tr>";
					
					
				}

			?>
			
			
		</tbody>
	</table>
	<?php
		} else {
			print "<h3>No Recommedations Found</h3>";
		}
	?>
</div>

  <script type="text/javascript">
    // Define your locations: HTML content for the info window, latitude, longitude
    var locations = [[<?php echo $info; ?>]];
    
    // Setup the different icons and shadows
    var iconURLPrefix = 'http://maps.google.com/mapfiles/ms/icons/';
    
    var icons = [ iconURLPrefix + 'red-dot.png' ]
    var icons_length = icons.length;
    
    
    var shadow = {
      anchor: new google.maps.Point(15,33),
      url: iconURLPrefix + 'msmarker.shadow.png'
    };

    var map = new google.maps.Map(document.getElementById('map'), {
      zoom: <?php echo $zoom; ?>,
      center: new google.maps.LatLng(<?php echo "{$lat}, {$lng}"; ?>),
      mapTypeId: google.maps.MapTypeId.ROADMAP,
      mapTypeControl: false,
      streetViewControl: false,
      panControl: false,
      zoomControlOptions: {
         position: google.maps.ControlPosition.LEFT_BOTTOM
      }
    });

    var infowindow = new google.maps.InfoWindow({
      maxWidth: 3000
    });

    var marker;
    var markers = new Array();
    
    var iconCounter = 0;
    
    // Add the markers and infowindows to the map
    for (var i = 0; i < locations.length; i++) {  
      marker = new google.maps.Marker({
        position: new google.maps.LatLng(locations[i][1], locations[i][2]),
        map: map,
        icon : icons[iconCounter],
        shadow: shadow
      });

      markers.push(marker);

      google.maps.event.addListener(marker, 'click', (function(marker, i) {
        return function() {
          infowindow.setContent(locations[i][0]);
          infowindow.open(map, marker);
        }
      })(marker, i));
      
      iconCounter++;
      // We only have a limited number of possible icon colors, so we may have to restart the counter
      if(iconCounter >= icons_length){
      	iconCounter = 0;
      }
    }
  </script> 
</body>
</html>