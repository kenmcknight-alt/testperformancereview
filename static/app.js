document.addEventListener("DOMContentLoaded", () => {
  const addQuestionBtn = document.getElementById("addQuestionBtn");
  const questionList = document.getElementById("questionList");

  if (!addQuestionBtn || !questionList) {
    return;
  }

  addQuestionBtn.addEventListener("click", () => {
    const wrapper = document.createElement("div");
    wrapper.className = "question-item border rounded p-2";
    wrapper.innerHTML = `
      <textarea class="form-control mb-2" name="prompt" rows="2" placeholder="Enter question..."></textarea>
      <div class="d-flex gap-2">
        <select class="form-select" name="answer_by">
          <option value="reviewer">Reviewer answers</option>
          <option value="reviewee">Reviewee answers</option>
          <option value="both" selected>Both answer</option>
        </select>
        <button class="btn btn-outline-danger" type="button">Remove</button>
      </div>
    `;

    wrapper.querySelector("button").addEventListener("click", () => wrapper.remove());
    questionList.appendChild(wrapper);
  });
});
