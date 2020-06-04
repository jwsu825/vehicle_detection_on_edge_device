var map;
var devices;
var markers;
var focusWindowInterval;
var focusWindowDeviceId;

var sumLong = 0;
var sumLat = 0;

var deviceToAdd = {};
var getCoordsListener;
var previewInterval;
var configInterval;
var saveConfigInterval;

var newP1;
var newP2;
var drawingLine = false;

function initMap(lat, long, zoom) {
    map = new google.maps.Map(document.getElementById('map'), {
        center: {lat: lat, lng: long},
        zoom: zoom,
        disableDefaultUI: true
    });
}

function centerMap(lat, long, zoom) {
    map.setOptions({
        center: {lat: lat, lng: long},
        zoom: zoom
    });
}

function convertEpochToDateString(time) {
    var date = new Date(time*1000);
    return date.getDate() + '/' + (date.getMonth() + 1) + '/' + date.getFullYear() + ' ' + date.getHours() + ':' + date.getMinutes() + ':' + date.getSeconds();
}

function addRowToTable(label, time) {
    var table = $('#focusGlanceTable');
    var newRow = document.createElement('tr');
    var labelColumn = document.createElement('td');
    labelColumn.innerText = label;
    var timeColumn = document.createElement('td');
    timeColumn.innerText = convertEpochToDateString(parseFloat(time));
    newRow.append(labelColumn);
    newRow.append(timeColumn);
    table.append(newRow);
}
function addTableHeaders() {
    var table = $('#focusGlanceTable');
    var tableHead = document.createElement('thead');
    var newRow = document.createElement('tr');
    var labelColumn = document.createElement('th');
    labelColumn.innerText = 'Category';
    var timeColumn = document.createElement('th');
    timeColumn.innerText = 'Time';
    newRow.append(labelColumn);
    newRow.append(timeColumn);
    table.append(newRow);
}

function updateEntriesInFocusTable(deviceID) {
    return function() {
        get(SERVER_ADDRESS + '/devices/' + devices[deviceID]['id'].toString() + '/entries', function(data) {
            var entries = JSON.parse(data)['data']['entries'];
            devices[deviceID]['entries'] = entries;
            addEntriesToFocusTable(deviceID);
        })
    }
}

function addEntriesToFocusTable(deviceID) {
    var table = $('#focusGlanceTable');
    table.empty();
    addTableHeaders();

    var entries = devices[deviceID]['entries'];

    for (var entry in devices[deviceID]['entries']) {
        addRowToTable(entries[entry]['category'], entries[entry]['time'])
    }

}

function showDeviceInFocusWindow(deviceID) {
    return function() {
        focusWindowDeviceId = deviceID;
        var focusDevice = devices[deviceID];
        $('#focusWindowTitle').text(focusDevice['name']);
        $('#focusLatInput').val(focusDevice['lat']);
        $('#focusLongInput').val(focusDevice['long']);
        $('#focusNameInput').val(focusDevice['name']);
        $('#focusLastCheckin').text(convertEpochToDateString(focusDevice['last-checkin']));

        get(SERVER_ADDRESS + "/devices/" + devices[deviceID]['id'].toString() + "/entries", function(data) {
            devices[deviceID]['entries'] = JSON.parse(data)['data']['entries'];
            addEntriesToFocusTable(deviceID);
            if (focusWindowInterval) {
                clearInterval(focusWindowInterval);
            }
            focusWindowInterval = setInterval(updateEntriesInFocusTable(deviceID), 2000);
        });


        var previewBtn = $('#getPreview');
        previewBtn.off('click');
        previewBtn.on('click', sendGetPictureCommand(deviceID));

        var configureBtn = $('#getConfigBtn');
        configureBtn.off('click');
        configureBtn.on('click', sendGetConfigCommand(deviceID));

        var putConfigureBtn = $('#saveConfigBtn');
        putConfigureBtn.off('click');
        putConfigureBtn.on('click', sendPutConfigCommand(deviceID));


        $('#focusWindow').show('fast');
    };
}

function chooseLatLng() {
    hideAddDeviceModal();
    getCoordsListener = map.addListener('click', function(event) {
        var lat = event.latLng.lat();
        var lng = event.latLng.lng();
        $('#addLatInput').val(lat.toString());
        $('#addLongInput').val(lng.toString());
        updateAddDevice();
        showAddDeviceModal();
        google.maps.event.removeListener(getCoordsListener);
    });

}

function getDevices() {
    get(SERVER_ADDRESS + '/devices', function(data) {
        var device;
        devices = JSON.parse(data)['data']['devices'];
        for (device in devices) {
            sumLong += devices[device]['long'];
            sumLat += devices[device]['lat'];
        }
        centerMap(sumLat/devices.length, sumLong/devices.length, 12);

        for (device in devices) {
            var tmpDev = devices[device];
            tmpDev['marker'] = new google.maps.Marker({
                position: {lat: tmpDev['lat'], lng: tmpDev['long']},
                map: map,
                animation: google.maps.Animation.DROP,
                title: tmpDev['name']
            });

            tmpDev['marker'].addListener('click', showDeviceInFocusWindow(device));
        }

    }, function(data, status, xhr) {
        console.log(status);
        checkAuth()
    });

}

function manageModalDisplay(display) {
    var modal = $("#loginModal");
    modal.modal({
        backdrop: 'static',
        keyboard: false
    });
    if (display){
        modal.modal("show");
    } else {
        modal.modal("hide");
    }
}

function showSearchModal() {
    var modal = $("#searchModal");
    modal.modal("show");

    $('#endSearchTime').datetimepicker();
    $('#startSearchTime').datetimepicker();
    populateSearchFields();
}

function sendGetPictureCommand(device_id){
    return function() {
        post(SERVER_ADDRESS + '/devices/' + devices[device_id]['id'].toString() + '/command', {'command': GET_PICTURE},
            function(data){
                var responseData = JSON.parse(data);
                var command_id = responseData['data']['command_id'];
                setConfigSuccess('Successfully put the get picture command. Should update shortly');
                clearInterval(previewInterval);
                previewInterval = setInterval(function() {
                    get(SERVER_ADDRESS + '/commands/' + command_id.toString(), function(command_data) {
                        var response = JSON.parse(command_data);
                        if (response['data']['status'] === 'completed')
                        {
                            setConfigSuccess('Successfully received a new image');
                            clearInterval(previewInterval);
                            var img = $('#previewImg');
                            img.attr('src', SERVER_ADDRESS + '/devices/' + devices[device_id]['id'].toString() + '/preview?' + (new Date).getTime());
                        }
                    }, function() {setConfigError('Failed to receive Image')});
                }, 1000);
            }, function(){setConfigError('Failed to put command')});
    }
}

function sendGetConfigCommand(device_id){
    return function() {
        post(SERVER_ADDRESS + '/devices/' + devices[device_id]['id'].toString() + '/command', {'command': GET_CONFIG},
            function(data){
                var command_id = JSON.parse(data)['data']['command_id'];
                setConfigSuccess('Successfully put the get configuration command');
                clearInterval(configInterval);
                configInterval = setInterval(function() {
                    get(SERVER_ADDRESS + '/commands/' + command_id.toString(), function(command_data){
                        var parsedData = JSON.parse(command_data)['data'];
                        if ('status' in parsedData && parsedData['status'] === 'completed')
                        {
                            setConfigSuccess('Successfully received the configuration from device.');
                            clearInterval(configInterval);
                            parsedData = parsedData['response']['data'];
                            var point1 = [parsedData['vehicle_detection']['point1x'], parsedData['vehicle_detection']['point1y']];
                            var point2 = [parsedData['vehicle_detection']['point2x'], parsedData['vehicle_detection']['point2y']];

                            drawCountline(point1, point2);
                            $('#currentConfig').val(JSON.stringify(parsedData, undefined, 4));
                            $('#newConfig').val(JSON.stringify(parsedData, undefined, 4));
                        }

                    }, function(){setConfigError('Failed to update the status of the command')});
                }, 1000);
            }, function(){setConfigError('Failed to put command')});
    }
}

function sendPutConfigCommand(device_id){
    return function() {
        var newConfig = JSON.parse($('#newConfig').val());
        post(SERVER_ADDRESS + '/devices/' + devices[device_id]['id'].toString() + '/command', {'command': SEND_CONFIG, 'data': newConfig},
            function(data){
                var command_id = JSON.parse(data)['data']['command_id'];
                setConfigSuccess('Successfully put command to update configuration. Will confirm it is complete soon');
                clearInterval(saveConfigInterval);
                saveConfigInterval = setInterval(function() {
                    get(SERVER_ADDRESS + '/commands/' + command_id.toString(), function(command_data){
                        var parsedData = JSON.parse(command_data)['data'];
                        if ('status' in parsedData && parsedData['status'] === 'completed')
                        {
                            setConfigSuccess('Configuration was successfully received by the device');
                            clearInterval(saveConfigInterval);
                        }
                    }, function(){setConfigError('Error retrieving command status')});
                }, 1000);
            }, function(){setConfigError('Failed to put command')});
    }
}

function showConfigureModal() {
    $('#configureSuccessAlert').hide();
    $('#configureErrorAlert').hide();
    resetConfigureWindow();
    var modal = $("#configureModal");
    modal.modal("show");
}

function addDevice() {
    $('#addDeviceSuccessAlert').hide();
    $('#addDeviceErrorAlert').hide();
    post(SERVER_ADDRESS + '/devices/add', deviceToAdd, function(data){
        var token = JSON.parse(data)['data']['token'];
        $('#tokenBox').text(token);
        $('#addDeviceSuccessAlert').show();
        getDevices();
    }, function(data) {
        var errorMsg = JSON.parse(data.responseText)['error']['message'];
        // console.log(data);
        $('#errorBox').text(errorMsg);
        $('#addDeviceErrorAlert').show();
    })
}

function deleteDeviceInFocusWindow() {
    post(SERVER_ADDRESS + "/devices/" + devices[focusWindowDeviceId]['id'].toString() + "/delete", {}, function(data) {
        console.log('device deleted');
        devices[focusWindowDeviceId]['marker'].setMap(null);
        closeFocusWindow();
    }, function() {
        console.log('failed to delete device');
    })
}

function showAddDeviceModal() {
    var modal = $("#addDeviceModal");
    modal.modal("show");
}

function hideAddDeviceModal() {
    var modal = $("#addDeviceModal");
    modal.modal("hide");
    $('#addDeviceSuccessAlert').hide();
    $('#addDeviceErrorAlert').hide();

}

function login() {
    var username = $("#loginUsername").val();
    var password = $("#loginPassword").val();

    $.post(SERVER_ADDRESS + '/login', {username: username, password: password}, function(data, status, xhr) {
        if (status === 'success') {
            var response = JSON.parse(data);
            var token = response['data']['token'];
            localStorage.setItem('token', token);
            // manageModalDisplay(false);
            showMainScreen();
        }
    })
}

function logout() {
    localStorage.setItem('token', '');
    checkAuth();
}

function showLoginScreen() {
    centerMap(STARTING_LAT, STARTING_LONG, STARTING_ZOOM);
    manageModalDisplay(true);
    $('#focusWindow').hide('fast');
    $('#btnCenter').hide('fast');
}

function showMainScreen() {
    $('#btnCenter').show();
    manageModalDisplay(false);
    getDevices();
}

function checkAuth() {
    checkToken(showLoginScreen);
}

function closeFocusWindow() {
    $('#focusWindow').hide('fast');
    clearInterval(focusWindowInterval);
}

function updateAddDevice() {
    deviceToAdd['name'] = $('#addNameInput').val();
    deviceToAdd['lat'] = parseFloat($('#addLatInput').val());
    deviceToAdd['long'] = parseFloat($('#addLongInput').val());
}

function addListeners() {
    var loginBtn = $("#loginBtn");
    loginBtn.on('click', login);
    var searchBtn = $("#searchBtn");
    searchBtn.on('click', showSearchModal);
    var addDeviceBtn = $("#addDeviceBtn");
    addDeviceBtn.on('click', showAddDeviceModal);
    var focusWindowSearchBtn = $("#focusWindowConfigureBtn");
    focusWindowSearchBtn.on('click', showConfigureModal);
    var logoutBtn = $("#logoutBtn");
    logoutBtn.on('click', logout);

    // focus window close btn
    var closeBtn = $('#focusWindowClose');
    closeBtn.on('click', closeFocusWindow);

    var addModal = $('#addDeviceModal');
    addModal.on('keyup', updateAddDevice);

    var chooseCoords = $('#clickPointOnMap');
    chooseCoords.on('click', chooseLatLng);


    var addDeviceSaveBtn = $('#addDeviceSaveBtn');
    addDeviceSaveBtn.on('click', addDevice);

    var deleteDeviceBtn = $('#deleteDeviceFocusWindow');
    deleteDeviceBtn.on('click', deleteDeviceInFocusWindow);

    var searchEntriesButton = $('#searchModalButton');
    searchEntriesButton.on('click', search);

}

function resetConfigureWindow() {
    $('#previewImg').attr('src', 'images/placeholder.jpg');
    paper.project.activeLayer.removeChildren();
    $('#currentConfig').val('');
    $('#newConfig').val('');

    newP1 = null;
    newP2 = null;
}

function drawCountline(point1, point2) {
    paper.project.activeLayer.removeChildren();
    var path = new paper.Path();
    path.strokeColor = 'red';
    var p1 = new paper.Point(point1[0], point1[1]);
    var p2 = new paper.Point(point2[0], point2[1]);

    path.moveTo(p1);
    path.lineTo(p2);
    paper.view.draw();
}

function updateNewConfig(point1, point2) {
    var newConfig = $('#newConfig');
    var parsedData = JSON.parse(newConfig.val());
    parsedData['vehicle_detection']['point1x'] = point1[0];
    parsedData['vehicle_detection']['point1y'] = point1[1];
    parsedData['vehicle_detection']['point2x'] = point2[0];
    parsedData['vehicle_detection']['point2y'] = point2[1];
    newConfig.val(JSON.stringify(parsedData, undefined, 4));
}

function setConfigSuccess(message) {
    $('#configureErrorAlert').hide();
    $('#configSuccessBox').text(message);
    $('#configureSuccessAlert').show();
}

function setConfigError(message) {
    $('#configureSuccessAlert').hide();
    $('#configSuccessBox').text(message);
    $('#configureErrorAlert').show();
}

window.addEventListener('load', function(){
    initMap(STARTING_LAT, STARTING_LONG, STARTING_ZOOM);
    addListeners();
    setInterval(checkAuth, 30000);
    getDevices();

    var canvas = document.getElementById('myCanvas');
    paper.setup(canvas);

    var tool = new paper.Tool();
    tool.onMouseDown = function(event){
        var curConfig = $('#currentConfig').val();
        if (curConfig === '')
            return;
        newP1 = [parseInt(event.point.x), parseInt(event.point.y)];
    };

    tool.onMouseDrag = function(event){
        if (newP1 === null)
            return;
        newP2 = [parseInt(event.point.x), parseInt(event.point.y)];
        drawCountline(newP1, newP2);
    };

    tool.onMouseUp = function(event) {
        if (newP1 === null || newP2 === null)
            return;
        newP2 = [parseInt(event.point.x), parseInt(event.point.y)];
        drawCountline(newP1, newP2);
        updateNewConfig(newP1, newP2);
    };
});
