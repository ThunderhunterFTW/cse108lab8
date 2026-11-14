const csrf = document.querySelector('meta[name="csrf-token"]').content;
const thead = document.getElementById('thead');
const tbody = document.getElementById('tbody');
const message = document.getElementById('message');
const tabs = { mine: document.getElementById('mine'), all: document.getElementById('all') };
let view = 'mine';

async function fetchStudents() {
    const response = await fetch(url, { method, headers: { 'X-CSRF-Token': csrf } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch students');
    }
    return data;
}

function cell(row, text){
    const td = document.createElement('td');
    td.textContent = text;
    row.appendChild(td);
    return td;
}

async function act(method, course){
    try {
        await api(`/api/enroll/${course.id}`,method);
        message.textContent = method === "POST" ? 'Enrolled in ${course.name}' : 'Unenrolled from ${course.name}';
    } catch (err) {
        message.textContent = err.message;
    }
    render(false);
}

async function render(clearMessage = true){
    if(clearMessage) message.textContent = '';
    tabs.mine.classList.toggle('active', view === 'mine');
    tabs.all.classList.toggle('active', view === 'all');
    const courses = await api(view === "mine" ? "/api/my-courses" : "/api/courses");
    thead.innerHTML = "";
    const head = thead.insertRow();
    ["Course Name", "Teacher", "Time", "Students Enrolled", ""].forEach((t) => {
        const th = document.createElement("th");
        th.textContent = t;
        head.appendChild(th);
    });
    tbody.innerHTML = "";
    if (!courses.length) {
        cell(tbody.insertRow(), "No courses to show").colSpan = 5;
        return;
    }
    for (const c of courses){
        const row = tbody.insertRow();
        cell(row, c.name);
        cell(row, c.teacher);
        cell(row, c.time);
        cell(row, '${c.enrolled}/${c.capacity}');
        const action = cell(row, "");
        const btn = document.createElement("button");
        if (c.enrolled_in) {
            btn.textContent = "Drop";
            btn.onclick = () => act('DELETE', c);
        } else if (c.full) {
            btn.texContent = "Full";
            btn.disabled = true;
        } else {
            btn.textContent = "add";
            btn.onclick = () => act("POST", c);
        }
        action.appendChild(btn);
    }
}

tabs.mine.onclick = () => { view = "mine"; render(); };
tabs.all.onclick = () => { view = "all"; render(); };
render();