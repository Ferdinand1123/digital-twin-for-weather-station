window.onload = function() {
    console.log('onload');
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

    fetch('/api/data-submission', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        list_available_datasets();
    })
    .catch(error => console.error('Error:', error));
    
}


function list_available_datasets() {
    fetch('/api/available-datasets')
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        const datasetList = document.getElementById('dataset-list');
        datasetList.innerHTML = '';
        data.forEach(dataset => {
            const listItem = document.createElement('li');
            // each list item should get a name and a button to execute fill in
            listItem.appendChild(document.createElement('span')).textContent = dataset.name;
            const ctaArea = listItem.appendChild(document.createElement('div'));
            ctaArea.classList.add('cta-area');
            if (dataset.has_model) {                
                ctaArea.appendChild(get_fill_in_button(dataset.uid));
            }
            ctaArea.appendChild(get_train_button(dataset.uid));
            ctaArea.appendChild(get_delete_button(dataset.uid));
            listItem.appendChild(ctaArea);
            datasetList.appendChild(listItem);
        });
    })
    .catch(error => console.error('Error:', error));
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
    .catch(error => console.error('Error:', error));
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
    }).then(
        () => list_available_datasets()
        )
    .catch(error => console.error('Error:', error));
}

function request_delete_for_dataset(uid) {
    fetch(`/api/delete-dataset/${uid}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        list_available_datasets();
    })
    .catch(error => console.error('Error:', error));
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