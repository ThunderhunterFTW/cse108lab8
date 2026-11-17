const csrf = document.querySelector('meta[name="csrf-token"]').content;
const title = document.getElementById('title');
const thead = document.getElementById('thead');
const tbody = document.getElementById('tbody');
const message = document.getElementById('message');
const back = document.getElementById('tab-back');

async function api(url, method = "GET", body = null) {
    const headers = { 'X-CSRFToken': csrf };
    if (body !== null) headers['Content-Type'] = 'application/json';
    const response = await fetch(url, { method, headers, body: body === null ? undefined : JSON.stringify(body) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || 'Request failed');
    }
    return data;
}

function cell(row, text){
    const td = document.createElement('td');
    td.textContent = text;
    row.appendChild(td);
    return td;
}

function header(labels){
    thead.innerHTML = "";
    const head = thead.insertRow();
    labels.forEach((t) => {
        const th = document.createElement("th");
        th.textContent = t;
        head.appendChild(th);
    });
}

async function showCourses(){
    message.textContent = '';
    title.textContent = 'Your Courses';
    back.classList.add('active');
    const courses = await api("/api/teacher/courses");
    header(["Course Name", "Teacher", "Time", "Students Enrolled", ""]);
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
        cell(row, `${c.enrolled}/${c.capacity}`);
        const btn = document.createElement("button");
        btn.textContent = "View students";
        btn.onclick = () => showRoster(c.id);
        cell(row, "").appendChild(btn);
    }
}

async function saveGrade(course, student, input){
    const text = input.value.trim();
    // empty box clears the grade
    const grade = text === "" ? null : Number(text);
    try {
        const data = await api(`/api/teacher/enrollments/${student.enrollment_id}`, "PATCH", { grade });
        student.grade = data.grade;
        message.textContent = `Saved grade for ${student.name}`;
    } catch (err) {
        message.textContent = err.message;
        input.value = student.grade === null ? "" : student.grade;
    }
}

async function showRoster(courseId){
    message.textContent = '';
    back.classList.remove('active');
    let data;
    try {
        data = await api(`/api/teacher/courses/${courseId}/students`);
    } catch (err) {
        message.textContent = err.message;
        return;
    }
    title.textContent = data.course.name;
    header(["Student Name", "Grade"]);
    tbody.innerHTML = "";
    if (!data.students.length) {
        cell(tbody.insertRow(), "No students enrolled").colSpan = 2;
        return;
    }
    for (const s of data.students){
        const row = tbody.insertRow();
        cell(row, s.name);
        const input = document.createElement("input");
        input.type = "number";
        input.min = 0;
        input.max = 100;
        input.step = 1;
        input.value = s.grade === null ? "" : s.grade;
        input.setAttribute("aria-label", `Grade for ${s.name}`);
        input.onchange = () => saveGrade(data.course, s, input);
        cell(row, "").appendChild(input);
    }
}

back.onclick = showCourses;
showCourses();
