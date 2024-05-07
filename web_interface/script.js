const socket = io();

window.onload = function(){
    
    update_available_datasets()
    setInterval(update_available_datasets, 1000);
}

function getUidFromCookie() {
        // set random unique id as cookie with expiration date in 1 year
        if (!document.cookie) {
            if (document.cookie.split('; ').find(row => row.startsWith("uid")) === undefined) {
                document.cookie = `uid=${Math.random().toString(36).substring(2)}; expires=${new Date(Date.now() + 31536000000).toUTCString()}`;
            }
        }   
        return document.cookie.split('; ').find(row => row.startsWith(name)).split('=')[1];
    }

function submitForm() {
    // Disable the submit button
    const submitButton = document.getElementById('submit_btn');
    submit_button_text_before = submitButton.textContent
    submitButton.disabled = true;
    submitButton.textContent = 'Uploading...';

    const measurementFiles = document.getElementById('measurement').files;
    let hasDatFile = false;
    let hasRtfFile = false;

    for (let i = 0; i < measurementFiles.length; i++) {
        const file = measurementFiles[i];
        if (file.name.endsWith('.dat')) {
            hasDatFile = true;
        } else if (file.name.endsWith('.rtf')) {
            hasRtfFile = true;
        } else if (file.name.endsWith('.zip')) {
            hasDatFile = true;
            hasRtfFile = true;
        }
    }

    if (!hasDatFile || !hasRtfFile) {
        alert('Please select at least one ".dat" file and one ".rtf" file as measurement files.');
        submitButton.textContent = submit_button_text_before;
        submitButton.disabled = false;   
        return;
    }

    const modelFile = document.getElementById('model').files[0];

    const formData = new FormData();
    for (let i = 0; i < measurementFiles.length; i++) {
        formData.append('measurements', measurementFiles[i]);
    }
    formData.append('model', modelFile);

    // append cookie to form data
    formData.append('cookie', getUidFromCookie());

    fetch('/api/data-submission', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        submitButton.textContent = submit_button_text_before;
        submitButton.disabled = false;
        request_available_datasets();
    })
    .catch(error => {
        console.error('Error:', error)
        submitButton.textContent = submit_button_text_before;
        submitButton.disabled = false;   
    });
}


function list_available_datasets(data) {
    console.log("Received data: ", data);
    const datasetList = document.getElementById('dataset-list');
    datasetList.innerHTML = '';
    if (data) {
        data.forEach(dataset => {
            const listItem = document.createElement('li');
            const listItemHead = listItem.appendChild(document.createElement('div'));
            // each list item should get a name and a button to execute fill in
            listItemHead.appendChild(document.createElement('span')).textContent = dataset.name;
            const ctaArea = listItem.appendChild(document.createElement('div'));
            ctaArea.classList.add('cta-area');
            if (dataset.status == "") {
                if (dataset.has_model) {                
                    ctaArea.appendChild(get_fill_in_button(dataset.uid));
                    ctaArea.appendChild(get_eval_as_pdf_button(dataset.uid));
                }
                ctaArea.appendChild(get_train_button(dataset.uid));
                ctaArea.appendChild(get_delete_button(dataset.uid));
            } else {
                ctaArea.appendChild(document.createElement('span')).textContent = dataset.status;
            }
            listItemHead.appendChild(ctaArea);
            listItem.appendChild(listItemHead);
            const downloadArea = listItem.appendChild(document.createElement('div'));
            downloadArea.classList.add('download-area');
            if (dataset.has_model) {
                downloadArea.appendChild(download_model_button(dataset.uid));
            }
            if (dataset.has_val_pdf) {
                downloadArea.appendChild(download_val_pdf_button(dataset.uid));
            }
            if (dataset.has_val_csv) {
                downloadArea.appendChild(download_val_csv_button(dataset.uid));
            }
            if (dataset.has_fill_in) {
                downloadArea.appendChild(download_infilling_tas_button(dataset.uid));
            }
            listItem.appendChild(downloadArea);
            datasetList.appendChild(listItem);
        });
    }
}

function request_available_datasets() {
    // if tab is not active, do not request data
    if (document.hidden) {
        return;
    }
    const cookie = getUidFromCookie();
    
    fetch('/api/available-datasets/' + cookie)
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => list_available_datasets(data))
    .catch(error => {
        console.error('Error:', error)
    });
}

function update_available_datasets() {
    
    if (document.hidden) {
        return;
    }
   // const cookie = getUidFromCookie();
   // socket.emit('request_available_datasets', cookie);
    
 request_available_datasets();
}

socket.on('available_datasets', data => {
    list_available_datasets(data);
});

function request_fill_in_for_dataset(uid) {
    fetch(`/api/fill-in/${uid}`)
    .then(response => download_any_file_from_response(response))
    .catch(error => {
        console.error('Error:', error)
    });
}

function request_train_for_dataset(uid, iterations) {
    fetch(`/api/train/${uid}?iterations=${iterations}`)
    .then(response => download_any_file_from_response(response))
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
        request_available_datasets();
    })
    .catch(error => {
        console.error('Error:', error)
    });
}

function validation_to_pdf(uid) {
    fetch(`/api/validate-model/${uid}`)
    .then(response => download_any_file_from_response(response))
    .catch(error => {
        console.error('Error:', error)
    });
}


function download_model_of_dataset(uid) {
    fetch(`/api/download-model/${uid}`)
    .then(response => download_any_file_from_response(response))
    .catch(error => {
        console.error('Error:', error)
    });
}

function download_validation_as_pdf(uid) {
    fetch(`/api/download-validation-pdf/${uid}`)
    .then(response => download_any_file_from_response(response))
    .catch(error => {
        console.error('Error:', error)
    });
}

function download_validation_as_csv(uid) {
    fetch(`/api/download-validation-csv/${uid}`)
    .then(response => download_any_file_from_response(response))
    .catch(error => {
        console.error('Error:', error)
    });
}

function download_infilling_as_tas(uid) {
    fetch(`/api/download-infilling/${uid}`)
    .then(response => download_any_file_from_response(response))
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
    trainButton.onclick = () => {
        const iterations = prompt("Enter the count of iterations:");
        if (iterations !== null && iterations.trim() !== "") {
            const parsedIterations = parseInt(iterations, 10);
            if (!isNaN(parsedIterations) && Number.isInteger(parsedIterations)) {
                request_train_for_dataset(uid, parsedIterations);
            } else {
                alert("Please enter a valid integer for iterations.");
            }
        }
    };
    return trainButton;
}

function get_delete_button(uid) {
    const deleteButton = document.createElement('button');
    deleteButton.textContent = 'Delete';
    deleteButton.onclick = () => request_delete_for_dataset(uid);
    return deleteButton;
}

function get_eval_as_pdf_button(uid) {
    const pdfButton = document.createElement('button');
    pdfButton.textContent = 'Evaluate'
    pdfButton.onclick = () => validation_to_pdf(uid);
    return pdfButton;
}

function download_model_button(uid) {
    const modelButton = document.createElement('button');
    modelButton.textContent = 'Download model'
    modelButton.onclick = () => download_model_of_dataset(uid);
    return modelButton
}

function download_val_pdf_button(uid) {
    const valPdfButton = document.createElement('button');
    valPdfButton.textContent = 'Download validation as PDF'
    valPdfButton.onclick = () => download_validation_as_pdf(uid);
    return valPdfButton
}

function download_val_csv_button(uid) {
    const valCsvButton = document.createElement('button');
    valCsvButton.textContent = 'Download validation as CSV'
    valCsvButton.onclick = () => download_validation_as_csv(uid);
    return valCsvButton
}

function download_infilling_tas_button(uid) {
    const infillingCsvButton = document.createElement('button');
    infillingCsvButton.textContent = 'Download infilling (.dat)'
    infillingCsvButton.onclick = () => download_infilling_as_tas(uid);
    return infillingCsvButton
}

function download_any_file_from_response(response){
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
}