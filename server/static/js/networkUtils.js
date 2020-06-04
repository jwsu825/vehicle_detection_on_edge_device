function post(url, data, callback, errorCallback) {
    $.ajax({
        type: 'POST',
        url: url,
        headers: {
            'Authorization': 'Token ' + localStorage.getItem('token')
        },
        success: callback,
        error: errorCallback,
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8"
    });
}

function get(url, callback, errorCallback) {
    $.ajax({
        type: 'GET',
        url: url,
        headers: {
            'Authorization': 'Token ' + localStorage.getItem('token')
        },
        success: callback,
        error: errorCallback
    });
}

function checkToken(errorCallback) {
    var token = localStorage.getItem('token');
    get(SERVER_ADDRESS + '/check-token', function(){}, errorCallback);
}