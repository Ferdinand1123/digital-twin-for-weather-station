window.onload = function(){
    // set random unique id as cookie with expiration date in 1 year
    if (!document.cookie) {
        document.cookie = `uid=${Math.random().toString(36).substring(2)}; expires=${new Date(Date.now() + 31536000000).toUTCString()}`;
    }
    list_available_datasets();
}

function submitForm() {
    const measurementFiles = document.getElementById('measurement').files;
    let hasDatFile = false;
    let hasRtfFile = false;

    for (let i = 0; i < measurementFiles.length; i++) {
        const file = measurementFiles[i];
        if (file.name.endsWith('.dat')) {
            hasDatFile = true;
        } else if (file.name.endsWith('.rtf')) {
            hasRtfFile = true;
        }
    }

    if (!hasDatFile || !hasRtfFile) {
        alert('Please select at least one ".dat" file and one ".rtf" file as measurement files.');
        return;
    }

    const modelFile = document.getElementById('model').files[0];

    const formData = new FormData();
    for (let i = 0; i < measurementFiles.length; i++) {
        formData.append('measurements', measurementFiles[i]);
    }
    formData.append('model', modelFile);

    // append cookie to form data
    const cookie = document.cookie.split('; ').find(row => row.startsWith('uid')).split('=')[1];
    formData.append('cookie', cookie);

    fetch('/api/data-submission', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
    })
    .catch(error => console.error('Error:', error));
}

// new function to list available datasets using a websocket and cookie

const cookie = document.cookie.split('; ').find(row => row.startsWith('uid')).split('=')[1];
// findout domain and port of the current page
const domain = window.location.hostname;
const port = window.location.port;
let baseUrl = '' 
if (window.location.protocol == 'https:') {
    baseUrl += 'wss://';
} else {
    baseUrl += 'ws://';
}
baseUrl += domain
if (port) {
    baseUrl += ':' + port;
}
const socket = new io(baseUrl, { query: { cookie: cookie } });

// Handle WebSocket events
socket.on('connect', () => {
    console.log('WebSocket connected');
})

socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
    list_available_datasets();
})

socket.on('update', data => {
    list_available_datasets(data);
})
    
function list_available_datasets(data) {
    console.log("Received data: ", data);
    const datasetList = document.getElementById('dataset-list');
    datasetList.innerHTML = '';
    if (data) {
        data.forEach(dataset => {
            const listItem = document.createElement('li');
            // each list item should get a name and a button to execute fill in
            listItem.appendChild(document.createElement('span')).textContent = dataset.name;
            const ctaArea = listItem.appendChild(document.createElement('div'));
            ctaArea.classList.add('cta-area');
            if (dataset.status == "") {
                if (dataset.has_model) {                
                    ctaArea.appendChild(get_fill_in_button(dataset.uid));
                }
                ctaArea.appendChild(get_train_button(dataset.uid));
                ctaArea.appendChild(get_delete_button(dataset.uid));
            } else {
                ctaArea.appendChild(document.createElement('span')).textContent = dataset.status;
            }
            listItem.appendChild(ctaArea);
            datasetList.appendChild(listItem);
        });
    }
}


function request_fill_in_for_dataset(uid) {
    fetch(`/api/fill-in/${uid}`)
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const filename = response.headers.get('content-disposition').split('filename=')[1];
        return response.blob().then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        });
    })
    .catch(error => {
        console.error('Error:', error)
    });
}

function request_train_for_dataset(uid) {
    fetch(`/api/train/${uid}`)
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const filename = response.headers.get('content-disposition').split('filename=')[1];
        return response.blob().then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        });
    })
    .catch(error => {
        console.error('Error:', error)
    });
}

function request_delete_for_dataset(uid) {
    fetch(`/api/delete-dataset/${uid}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
    })
    .catch(error => {
        console.error('Error:', error)
    });
}


function get_fill_in_button(uid) {
    const fillInButton = document.createElement('button');
    fillInButton.textContent = 'Fill in';
    fillInButton.onclick = () => request_fill_in_for_dataset(uid);
    return fillInButton;
}

function get_train_button(uid) {
    const trainButton = document.createElement('button');
    trainButton.textContent = 'Train';
    trainButton.onclick = () => request_train_for_dataset(uid);
    return trainButton;
}

function get_delete_button(uid) {
    const deleteButton = document.createElement('button');
    deleteButton.textContent = 'Delete';
    deleteButton.onclick = () => request_delete_for_dataset(uid);
    return deleteButton;
}