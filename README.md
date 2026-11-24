# Flask School ERP – CBSE Classes 1–10

## 1. Project Overview

The **Flask School ERP (Enterprise Resource Planning) System** is a web-based application developed to manage the academic and administrative activities of a school.

The system is developed using Python Flask and MySQL. It provides separate portals for Admin, Teachers, and Students. Each user can access the features according to their assigned role.

The main objective of this project is to simplify school management activities, reduce manual work, maintain student records, and improve communication between administrators, teachers, and students.

## 2. Project Objectives

- To develop a centralized school management system.
- To maintain student and staff information.
- To manage classes, subjects, and teacher assignments.
- To record and monitor student attendance.
- To manage examinations and student marks.
- To maintain student fee records and payments.
- To provide separate dashboards for Admin, Teachers, and Students.
- To provide secure role-based access to the system.

## 3. Modules and Features

### 3.1 Admin Module

The Admin module is responsible for managing the overall school activities.

Features:

- Admin login and dashboard.
- Student management, including adding, viewing, and updating student details.
- Class and subject management.
- Teacher and staff information management.
- Assigning teachers to classes and subjects.
- Viewing teacher assignments.
- Managing student fee records.
- Recording and managing fee payments.
- Monitoring school information.

### 3.2 Teacher Module

The Teacher module provides facilities for teachers to manage their assigned academic activities.

Features:

- Teacher login and dashboard.
- Viewing assigned classes and subjects.
- Viewing student details.
- Searching and filtering student records.
- Recording daily student attendance.
- Navigating attendance records by date.
- Creating and managing examinations.
- Entering and updating student marks.
- Viewing examination details.

### 3.3 Student Module

The Student module allows students to view their academic and personal information.

Features:

- Student login and dashboard.
- Viewing personal and academic details.
- Viewing enrolled subjects.
- Checking attendance records.
- Viewing examination marks and grades.
- Checking fee balances.
- Viewing parent or guardian contact information.

## 4. Technologies Used

| Technology       | Purpose                           |
| ---------------- | --------------------------------- |
| Python           | Backend programming               |
| Flask            | Web application framework         |
| HTML             | Web page structure                |
| CSS              | Web page styling                  |
| Jinja2           | Dynamic HTML templates            |
| MySQL            | Database management               |
| Flask-SQLAlchemy | Database integration              |
| Flask-Login      | User authentication               |
| Flask-WTF        | Form handling and CSRF protection |
| PyMySQL          | MySQL connectivity                |
| python-dotenv    | Environment variable management   |

## 5. Database Design

The project uses a MySQL database named `school_erp`.

The database contains the following 11 tables:

1. `user` – Stores user login and account information.
2. `student_profile` – Stores student details.
3. `staff_profile` – Stores staff and teacher details.
4. `class_room` – Stores class and section information.
5. `subject` – Stores subject information.
6. `teaching_assignment` – Stores teacher, class, and subject assignments.
7. `attendance` – Stores student attendance records.
8. `exam` – Stores examination information.
9. `mark` – Stores student examination marks.
10. `fee_record` – Stores student fee information.
11. `fee_payment` – Stores fee payment records.

The database structure is provided in `schema.sql`.

## 6. Project Folder Structure

```text
flask_school_erp/
│
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
├── README.md
├── schema.sql
├── .env.example
├── .gitignore
│
├── templates/
│   ├── admin_dashboard.html
│   ├── teacher_base.html
│   ├── student_dashboard.html
│   └── other HTML templates
│
├── tests/
│   └── smoke_test.py
│
├── reports/
│   ├── Mid-Term Report
│   └── Final Project Report
│
└── Project_Photos/
    └── Project screenshots
```


## 7. Installation and Setup

### Step 1: Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd flask_school_erp
```

### Step 2: Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate the virtual environment on macOS/Linux:

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create the MySQL Database

Open MySQL and execute:

```sql
CREATE DATABASE school_erp;
```

### Step 5: Configure Environment Variables

Create a `.env` file using the example file:

```bash
cp .env.example .env
```

Open `.env` and configure your MySQL connection:

```env
SECRET_KEY=your-secret-key
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=school_erp
DB_USER=your_mysql_username
DB_PASSWORD=root
```


### Step 6: Initialize Database Tables

Run:

bash
flask --app app init-db


This command creates missing database tables.

Alternatively, the exported database structure is available in `schema.sql`. To import it into MySQL:

bash
mysql -u root -p school_erp < schema.sql


Use either the schema import or the initialization command as appropriate for the database setup. Do not import the schema over an existing database without checking its contents first.

### Step 7: Update Exam Room Column

Run:

bash
flask --app app add-exam-room-column


This command checks whether the `room` column exists in the `exam` table and adds it if missing.

### Step 8: Insert Default Classes and Subjects

Run:

bash
flask --app app seed-school


This command inserts default classes from 1 to 10, Section A, academic year 2026–2027, and the default subjects if they do not already exist.

## 8. Running the Application

After completing the setup, start the Flask application using the command:

bash
python app.py


Open the local application URL shown in the terminal in your web browser.

## 9. Security Features

- Role-based access control for Admin, Teacher, and Student users.
- Password hashing using Werkzeug.
- Login management using Flask-Login.
- CSRF protection using Flask-WTF.
- Restricted access to role-specific pages.
- Database transaction handling and rollback for relevant operations.
- Environment variables for sensitive configuration.

## 10. Testing

The project includes a `tests/` directory containing a smoke test.

Test files can be executed using Python:

bash
python -m unittest discover -s tests


Testing covers application functionality and helps identify errors during development.

## 11. Project Reports and Photos

The GitHub repository includes the project documentation and implementation evidence.

- Mid-Term Report:** Contains the initial project design, literature survey, proposed methodology, diagrams, and initial implementation.
- Final Project Report:** Contains the complete project documentation, system design, implementation, database design, testing, results, and conclusion.
- Project Photos:** Contains screenshots demonstrating the application interfaces and implemented modules.

## 12. Future Enhancements

- Online fee payment integration.
- Parent login portal.
- Automated attendance notifications.
- Improved report generation.
- Mobile-friendly application interface.
- Additional academic performance analytics.

## 13. Team Members

| S. No. | Name               | Enrollment Number |
| ------ | ------------------ | ----------------- |
| 1      | Thrishu Sena Reddy | 24STUCHH010197    |
| 2      | Moltati Dhanush    | 24STUCHH010157    |
| 3      | Samba Sonalika     | 24STUCHH010102    |
| 4      | G Sai Charan       | 24STUCHH013006    |

## 14. Project Guide

**Guide:** VVS Satyanarayana Murthy

## 15. Conclusion

The Flask School ERP System provides a centralized platform for managing school activities. It simplifies administrative operations, supports teachers in managing academic records, and allows students to access their academic information.

The application uses Python Flask for backend development and MySQL for database management. The project demonstrates the practical implementation of a role-based web application for school management.

---

Project:Flask School ERP – CBSE Classes 1–10
Backend:Python Flask
Database: MySQL
Project Type: Web-Based School Management System
