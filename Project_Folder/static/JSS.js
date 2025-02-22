// Function to reserve a seat
async function reserveSeat(seatNumber, location) {
    if (confirm('Do you want to reserve this seat for 1 minute?')) {
        const studentId = "{{ session['student_id'] }}";  // Get the logged-in student ID from the session
        const response = await fetch("/reserve", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: studentId, seat_number: seatNumber, location: location })
        });
        const result = await response.json();
        if (result.status === "success") {
            alert(result.message);
            window.location.reload();  // Reload the page to reflect the changes
        } else {
            alert(result.message);  // Show error message if the seat cannot be reserved
        }
    }
}

// Function to occupy a seat
async function occupySeat(seatNumber, location) {
    if (confirm('Do you want to occupy this seat?')) {
        const studentId = "{{ session['student_id'] }}";  // Get the logged-in student ID from the session
        const response = await fetch("/occupy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: studentId, seat_number: seatNumber, location: location })
        });
        const result = await response.json();
        if (result.status === "success") {
            alert(result.message);
            window.location.reload();  // Reload the page to reflect the changes
        } else {
            alert(result.message);  // Show error message if the seat cannot be occupied
        }
    }
}