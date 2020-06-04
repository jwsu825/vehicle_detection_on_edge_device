
// <label><input type="checkbox" value="">Option 1</label>

var categories = ['pickup truck', 'background', 'work van', 'motorcycle', 'car', 'articulated truck', 'bus',
    'bicycle', 'non motorized vehicle', 'single unit truck', 'pedestrian'];

function addDeviceToDiv(divElement, deviceId) {
    var div = document.createElement('div');
    div.setAttribute('class', 'checkbox');
    var outerLabel = document.createElement('label');
    var checkbox = document.createElement('input');
    checkbox.setAttribute("type", "checkbox");
    checkbox.setAttribute("id", devices[deviceId]['id']);
    outerLabel.append(checkbox);
    var label = devices[deviceId]['name'];
    outerLabel.append(label);
    div.append(outerLabel);
    divElement.append(div);
}

function addCategories(divElement, category) {
    var div = document.createElement('div');
    div.setAttribute('class', 'checkbox');
    var outerLabel = document.createElement('label');
    var checkbox = document.createElement('input');
    checkbox.setAttribute("type", "checkbox");
    checkbox.setAttribute("id", category);
    outerLabel.append(checkbox);
    outerLabel.append(category);
    div.append(outerLabel);
    divElement.append(div);
}

function populateSearchFields() {
    var device;
    var checkBoxElement = $('#deviceCheckboxes');
    var categoryElement = $('#searchCategories');
    checkBoxElement.empty();
    categoryElement.empty();
    for (device in devices) {
        // var tmpDev = devices[device];
        addDeviceToDiv(checkBoxElement, device);
    }

    for (var category in categories) {
        addCategories(categoryElement, categories[category]);
    }
}

function getIdString() {
    var idString = 'ids=';
    var idElements = $('#deviceCheckboxes > div.checkbox > label > input');
    idElements.each(function(id) {
        var element = $(idElements[id]);
        if (element.prop('checked')) {
            idString += element.attr('id');
            idString += ',';
        }
    });
    if (idString === 'ids=')
        return null;
    idString = idString.slice(0, -1);
    return idString;
}

function getCategoryString() {
    var categoryString = 'cat=';
    var idElements = $('#searchCategories > div.checkbox > label > input');
    idElements.each(function(id) {
        var element = $(idElements[id]);
        if (element.prop('checked')) {
            categoryString += element.attr('id');
            categoryString += ',';
        }
    });
    if (categoryString === 'cat=')
        return null;
    categoryString = categoryString.slice(0, -1);
    return categoryString;
}

function addSearchTableHeaders() {
    var table = $('#searchResults');
    var tableHead = document.createElement('thead');
    var newRow = document.createElement('tr');
    var deviceColumn = document.createElement('th');
    deviceColumn.innerText = 'Device';
    var labelColumn = document.createElement('th');
    labelColumn.innerText = 'Category';
    var timeColumn = document.createElement('th');
    timeColumn.innerText = 'Time';
    newRow.append(deviceColumn);
    newRow.append(labelColumn);
    newRow.append(timeColumn);
    table.append(newRow);
}

function addRowToSearchTable(label, time, name) {
    var table = $('#searchResults');
    var newRow = document.createElement('tr');
    var deviceColumn = document.createElement('td');
    deviceColumn.innerText = name;
    var labelColumn = document.createElement('td');
    labelColumn.innerText = label;
    var timeColumn = document.createElement('td');
    timeColumn.innerText = convertEpochToDateString(parseFloat(time));
    newRow.append(deviceColumn);
    newRow.append(labelColumn);
    newRow.append(timeColumn);
    table.append(newRow);
}

function deviceIdToName(devId) {
    for(var device in devices) {
        var tmpDevice = devices[device];
        if (tmpDevice['id'] === devId)
            return tmpDevice['name'];
    }
    return null;
}

function updateSearchResults(data) {
    var entries = JSON.parse(data)['data']['entries'];
    console.log(entries);
    var table = $('#searchResults');
    table.empty();
    addSearchTableHeaders();
    for (var entry in entries) {
        var tmpEntry = entries[entry];
        addRowToSearchTable(tmpEntry['category'],
            tmpEntry['time'],
            deviceIdToName(tmpEntry['id']));
    }

}

function search() {
    var idString = getIdString();
    var categoryString = getCategoryString();

    var startTime = $('#startSearchTime').data("DateTimePicker").date();
    var endTime = $('#endSearchTime').data("DateTimePicker").date();
    // var nowMoment = moment().unix();

    var fullQueryString = '?';
    if (idString !== null) {
        fullQueryString += idString;
        fullQueryString += '&';
    }

    if (categoryString !== null) {
        fullQueryString += categoryString;
        fullQueryString += '&';
    }

    if (startTime !== null) {
        fullQueryString += 'min=' + String(startTime.unix());
        fullQueryString += '&';
    }

    if (endTime !== null) {
        fullQueryString += 'max=' + String(endTime.unix());
        fullQueryString += '&';
    }

    console.log(fullQueryString);

    get(SERVER_ADDRESS + '/devices/entries' + fullQueryString, updateSearchResults, function(data) {
        console.log('error in search');
    });

}