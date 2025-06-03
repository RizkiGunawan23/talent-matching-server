import datetime

from celery import shared_task
from django.utils import timezone
from neomodel import db

from core.matchers.matchers_functions import matching_after_scraping
from core.models import ScrapingTask
from core.scrapers.main_scraper import scrape_all_websites


@shared_task(bind=True)
def scrape_job_data(self):
    """Task Celery untuk scraping data"""
    task_id = self.request.id

    try:
        result = scrape_all_websites(task_id, self.update_state)
        return result
    except Exception as e:
        # Update scraping task status to ERROR when exception occurs
        try:
            scraping_task = ScrapingTask.nodes.filter(uid=task_id).first_or_none()
            if scraping_task:
                db.begin()
                try:
                    scraping_task.status = "ERROR"
                    scraping_task.message = "Scraping task failed due to an error."
                    scraping_task.save()
                    db.commit()
                except Exception as db_error:
                    db.rollback()
                    print(f"Failed to update scraping task status: {db_error}")
        except Exception as update_error:
            print(f"Error updating task status: {update_error}")

        # Re-raise the exception so Celery marks the task as FAILURE
        raise e


@shared_task(bind=True)
def matching_job_after_scraping(self, jobs_data=[]):
    jobs_data = [
        {
            "job_url": "https://glints.com/id/opportunities/jobs/full-stack-web-developer/614a8e49-c174-4b7e-b71c-737b97ca0ea1?utm_referrer=explore&traceInfo=9340957b-cf4a-43d2-b677-7b72efc50ad3",
            "image_url": "https://images.glints.com/unsafe/1920x0/glints-dashboard.oss-ap-southeast-1.aliyuncs.com/company-logo/681f9a1ff7c7f189fe4edebe8eff3f3f.png",
            "job_title": "Full Stack Web Developer",
            "company_name": "Yoona Digital Indonesia",
            "subdistrict": "Kebayoran Lama",
            "city": "Jakarta Selatan",
            "province": "DKI Jakarta",
            "minimum_salary": 8000000,
            "maximum_salary": 12000000,
            "employment_type": "Penuh Waktu",
            "work_setup": "Kerja di kantor atau rumah",
            "minimum_education": "Sarjana (S1)",
            "minimum_experience": 3,
            "maximum_experience": 5,
            "required_skills": [
                "MongoDB",
                "PostgreSQL",
                "Python",
                "whatsapp api",
                "WordPress Development",
                "Express",
                "JavaScript",
                "hugging face",
                "GitHub",
                "API Development",
                "woocommerce",
                "Git",
                "Next",
                "REST API",
                "Database",
                "Artificial Intelligence",
                "Node.js",
                "PHP",
                "ai/ml",
                "React",
                "PyTorch",
            ],
            "job_description": "<p><strong>Job Descriptions</strong></p><ul><li>Membangun dan memelihara frontend berbasis ReactJS</li><li>Merancang dan mengembangkan backend API menggunakan NodeJS dan ExpressJS</li><li>Mengembangkan dan memelihara website utama yoona (dot) id menggunakan WordPress / WooCommerce</li><li>Membuat modul AI sederhana atau mengintegrasikan model berbasis Python (misalnya dengan PyTorch, Hugging Face, atau API internal)</li><li>Melakukan integrasi dengan layanan pihak ketiga seperti payment gateway, WhatsApp API, dan AI inference server</li><li>Mengelola database (PostgreSQL atau MongoDB) dan infrastruktur API yang scalable</li><li>Memastikan keamanan, performa, dan dokumentasi dari setiap modul yang dibangun</li></ul><p><strong>Job Requirements</strong></p><ul><li>Minimal 2 tahun pengalaman sebagai Full Stack Developer</li><li>Pengalaman kerja nyata dengan ReactJS dan ekosistemnya (NextJS adalah nilai tambah)</li><li>Pengalaman backend dengan NodeJS, ExpressJS, dan REST API</li><li>Pengalaman dengan Wordpress WooCommerce</li><li>Pengalaman pengembangan dengan Python, terutama dalam konteks AI/ML (misalnya integrasi model, NLP, atau rekomendasi sistem)</li><li>Familiar dengan PostgreSQL, MongoDB, Git, dan deployment di platform cloud (Vercel, Render, Heroku, atau VPS)</li><li>Mampu bekerja secara mandiri maupun dalam tim kecil</li><li>Minimal 3 tahun pengalaman sebagai Full Stack Developeriasa dengan lingkungan startup yang dinamis3</li></ul><p><strong>How to Apply</strong></p><p>Kirim CV, portofolio (GitHub / projek live), dan perkenalan singkat kenapa kamu cocok untuk peran ini ke:  career (at) yoona (dot) id</p><p>Subject email: Full Stack Developer – [Nama Kamu]</p>",
            "scraped_at": "2025-06-03T15:34:24.885565",
        },
        {
            "job_url": "https://glints.com/id/opportunities/jobs/quality-assurance-enginer/52e864ac-400c-4636-bc34-1560ca83ba34?utm_referrer=explore&traceInfo=9340957b-cf4a-43d2-b677-7b72efc50ad3",
            "image_url": "https://images.glints.com/unsafe/1920x0/glints-dashboard.oss-ap-southeast-1.aliyuncs.com/company-logo/4b4c35fe615129e5c65c3f9b08c86e9f.png",
            "job_title": "Quality Assurance enginer",
            "company_name": "GoTechno",
            "subdistrict": "Serpong Utara",
            "city": "Tangerang Selatan",
            "province": "Banten",
            "minimum_salary": 4000000,
            "maximum_salary": 7000000,
            "employment_type": "Penuh Waktu",
            "work_setup": "Kerja di kantor",
            "minimum_education": "SMA/SMK",
            "minimum_experience": None,
            "maximum_experience": None,
            "required_skills": [
                "Software Testing",
                "Automation Testing",
                "Scrum",
                "Agile",
                "Postman",
                "Jira",
                "Software Quality Assurance",
                "SQL",
                "api testing",
                "Selenium",
                "Katalon",
                "QA Automation",
                "Manual Testing",
            ],
            "job_description": "<p>Kami mencari seorang QA Engineer yang teliti dan berorientasi pada detail untuk memastikan kualitas produk digital kami tetap tinggi. Anda akan bekerja sama dengan tim developer dan product untuk melakukan pengujian aplikasi, mengidentifikasi bug, serta memastikan sistem berjalan sesuai standar kualitas.</p><p>Tanggung Jawab:</p><ul><li>Membuat dan menjalankan test case untuk memastikan aplikasi berjalan sesuai spesifikasi.</li><li>Melakukan pengujian fungsional, regresi, integrasi, dan performa secara manual maupun otomatis.</li><li>Berkolaborasi dengan developer dan product manager untuk memahami kebutuhan produk dan merancang skenario pengujian.</li><li>Mencatat dan melaporkan bug secara sistematis, serta memantau proses penyelesaiannya.</li><li>Membantu menyusun dokumentasi terkait pengujian dan kualitas aplikasi.</li><li>Berkontribusi dalam pengembangan proses QA agar lebih efisien dan otomatis.</li></ul><p></p><p>Kualifikasi:</p><ul><li>Pendidikan minimal D3/S1 di bidang Teknik Informatika, Sistem Informasi, atau bidang terkait.</li><li>Memahami siklus hidup pengembangan perangkat lunak (SDLC) dan proses QA.</li><li>Mampu membuat test case dan test plan yang efektif.</li><li>Berpengalaman menggunakan tools seperti Postman, JIRA, Selenium, Katalon, atau sejenis.</li><li>Teliti, analitis, dan mampu berpikir kritis dalam mengidentifikasi masalah.</li><li>Mampu bekerja secara tim maupun mandiri, serta memiliki komunikasi yang baik.</li></ul><p><br>Nilai Tambah Jika Memiliki:</p><ul><li>Pengalaman dengan automation testing.</li><li>Memahami basic API testing dan SQL.</li><li>Pernah bekerja dalam lingkungan Agile/Scrum.</li></ul><p></p><p></p>",
            "scraped_at": "2025-06-03T15:34:32.328677",
        },
        {
            "job_url": "https://glints.com/id/opportunities/jobs/full-stack-developer/fdd0a646-f804-4dc3-b4b2-d361180feb28?utm_referrer=explore&traceInfo=9340957b-cf4a-43d2-b677-7b72efc50ad3",
            "image_url": "https://images.glints.com/unsafe/1920x0/glints-dashboard.oss-ap-southeast-1.aliyuncs.com/company-logo/4b4c35fe615129e5c65c3f9b08c86e9f.png",
            "job_title": "Full Stack Developer",
            "company_name": "GoTechno",
            "subdistrict": "Serpong Utara",
            "city": "Tangerang Selatan",
            "province": "Banten",
            "minimum_salary": 4000000,
            "maximum_salary": 8000000,
            "employment_type": "Penuh Waktu",
            "work_setup": "Kerja di kantor",
            "minimum_education": "SMA/SMK",
            "minimum_experience": None,
            "maximum_experience": None,
            "required_skills": [
                "MongoDB",
                "Angular",
                "Vue",
                "Docker",
                "PostgreSQL",
                "AWS",
                "TypeScript",
                "Python",
                "unit testing",
                "JavaScript",
                "UI/UX",
                "API Development",
                "Django",
                "Laravel",
                "Flask",
                "Google Cloud Platform",
                "Trello",
                "Git",
                "HTML5",
                "REST API",
                "Database",
                "Node.js",
                "CI/CD",
                "PHP",
                "Jira",
                "React",
                "CSS",
                "MySQL",
            ],
            "job_description": "<p>Kami mencari seorang Fullstack Developer yang bersemangat dan berpengalaman untuk bergabung dengan tim kami. Anda akan bertanggung jawab dalam pengembangan aplikasi web dari sisi frontend hingga backend, serta memastikan performa, skalabilitas, dan keamanan aplikasi berjalan optimal.</p><p></p><p>Tanggung Jawab:</p><ul><li>Membangun dan mengembangkan fitur frontend menggunakan framework modern seperti React, Vue, atau Angular.</li><li>Mengembangkan dan mengelola backend API menggunakan Nodejs, Laravel, atau teknologi sejenis.</li><li>Berkolaborasi dengan tim UI/UX, QA, dan product untuk memastikan kualitas produk.</li><li>Melakukan integrasi dengan database (MySQL, PostgreSQL, MongoDB).</li><li>Menyusun dokumentasi teknis dan melakukan perbaikan bug secara berkala.</li><li>Menyediakan dukungan teknis untuk aplikasi yang sudah berjalan.</li></ul><p></p><p>Kualifikasi:</p><ul><li>Menguasai JavaScript/TypeScript, HTML, CSS, dan salah satu framework frontend (React/Vue/Angular)</li><li>Menguasai Nodejs, PHP (Laravel), atau Python (Django/Flask).</li><li>Memahami konsep REST API dan integrasinya.</li><li>Berpengalaman menggunakan Git dan tools kolaborasi seperti Jira, Trello, atau sejenis.</li><li>Memiliki kemampuan analisis dan pemecahan masalah yang baik.</li><li>Mampu bekerja tim dan individu, serta terbiasa dengan deadline.</li></ul><p></p><p>Nilai Tambah Jika Memiliki:</p><ul><li>Pengalaman dengan Docker, CI/CD, dan cloud services (AWS, GCP, dsb).</li><li>Pernah membangun aplikasi PWA atau mobile-friendly web apps.</li><li>Familiar dengan unit testing dan TDD.</li></ul><p></p><p>Benefit:</p><p>Gaji kompetitif (disesuaikan dengan skill &amp; pengalaman)</p><p>Tunjangan makan &amp; transportasi</p>",
            "scraped_at": "2025-06-03T15:34:43.272206",
        },
        {
            "job_url": "https://glints.com/id/opportunities/jobs/back-end-developer/02c9b9e9-8967-4038-822e-958ce1ededfc?utm_referrer=explore&traceInfo=9340957b-cf4a-43d2-b677-7b72efc50ad3",
            "image_url": "https://images.glints.com/unsafe/1920x0/glints-dashboard.oss-ap-southeast-1.aliyuncs.com/company-logo/53443129cd483a998ac35a3f692eb51c.png",
            "job_title": "Back-end Developer",
            "company_name": "PT Guestpedia Harmoni Indonesia",
            "subdistrict": "Kapanewon Gamping",
            "city": "Kab. Sleman",
            "province": "DI Yogyakarta",
            "minimum_salary": 2500000,
            "maximum_salary": 5000000,
            "employment_type": "Penuh Waktu",
            "work_setup": "Kerja di kantor atau rumah",
            "minimum_education": "Sarjana (S1)",
            "minimum_experience": None,
            "maximum_experience": None,
            "required_skills": [
                "Node.js",
                "Back-End Web Development",
                "Express",
                "Software Development",
                "JavaScript",
                "Git",
                "Agile",
                "Frontend Development",
                "SQL",
                "REST API",
                "Database",
                "API Development",
            ],
            "job_description": "<p>Backend Developer </p><p>Location: Yogyakarta (Remote)</p><p>Employment Type: Full-Time/Part-Time/Freelance</p><p></p><p>We are looking for a talented Backend Developer to join our team. If you're passionate about building robust and scalable applications, this is the role for you!</p><p></p><p>Key Responsibilities:</p><p>•⁠  ⁠Design, develop, and maintain server-side applications using Express and JavaScript.</p><p>•⁠  ⁠Work on APIs and databases.</p><p>•⁠  ⁠Write clean and maintainable code.</p><p>•⁠  ⁠Troubleshoot and optimize backend performance.</p><p>•⁠  ⁠Collaborate with front-end developers.</p><p></p><p>Technical Requirements:</p><p>•⁠  ⁠Strong experience with Express and JavaScript .</p><p>•⁠  ⁠Proficient in RESTful APIs, middleware, and back-end integration.</p><p>•⁠  ⁠Knowledge of databases SQL and query optimization.</p><p>•⁠  ⁠Experience with Git version control and agile development practices.</p><p></p><p>Nice to Have:</p><p>•⁠  ⁠Familiarity with Node.js and cloud-based platforms.</p><p></p><p>Please send your resume and portfolio</p>",
            "scraped_at": "2025-06-03T15:34:50.842479",
        },
        {
            "job_url": "https://glints.com/id/opportunities/jobs/full-stack-developer/86bf6b24-77fd-4f8d-913d-ed3269c835c1?utm_referrer=explore&traceInfo=9340957b-cf4a-43d2-b677-7b72efc50ad3",
            "image_url": "https://images.glints.com/unsafe/1920x0/glints-dashboard.oss-ap-southeast-1.aliyuncs.com/company-logo/d02a940c757a3b86acae7550ce2d85bf.png",
            "job_title": "Full Stack Developer",
            "company_name": "PT Panduwan Aditian Teknologi",
            "subdistrict": "Kalideres",
            "city": "Jakarta Barat",
            "province": "DKI Jakarta",
            "minimum_salary": 4100000,
            "maximum_salary": 6000000,
            "employment_type": "Penuh Waktu",
            "work_setup": "Kerja di kantor",
            "minimum_education": "SMA/SMK",
            "minimum_experience": 1,
            "maximum_experience": 3,
            "required_skills": [
                "Vue",
                "Go",
                "Machine Learning",
                "Python",
                "JavaScript",
                "API Development",
                "Django",
                "Laravel",
                "NoSQL",
                "machine learning models",
                "SQL",
                "REST API",
                "Database",
                "Artificial Intelligence",
                "Software Engineering",
                "Node.js",
                "PHP",
                "Software Development",
                "Automation",
                "React",
            ],
            "job_description": "<p><strong>Tugas dan Tanggung Jawab:</strong></p><ul><li>Mengembangkan aplikasi web full-stack dari sisi frontend dan backend.</li><li>Berkolaborasi dengan tim produk untuk membangun fitur berbasis AI.</li><li>Mengintegrasikan AI ke dalam workflow aplikasi (bisa berupa chatbot, rekomendasi, automasi, dsb.)</li><li>Meningkatkan performa dan skalabilitas sistem.</li><li>Menyusun dokumentasi teknis dan melakukan pengujian berkala.</li></ul><p></p><p><strong>Kualifikasi :</strong></p><ul><li>Memiliki pengalaman sebagai Full Stack Developer minimal 1 tahun.</li><li>Pernah mengembangkan atau mengintegrasikan teknologi AI (contoh: chatbot, image processing, NLP, machine learning models, dsb.)</li><li>Menguasai minimal 2 bahasa pemrograman yang umum digunakan dalam pengembangan AI (seperti PHP, Python, JavaScript, Go, dll.)</li><li>Familiar dengan framework backend seperti Node.js, Django, atau Laravel.</li><li>Menguasai pengembangan frontend modern (React, Vue.js, atau lainnya).</li><li>Memahami konsep REST API &amp; integrasi dengan third-party services.</li><li>Berpengalaman dengan database (SQL/NoSQL).</li><li>Memiliki portofolio atau project AI yang bisa ditunjukkan adalah nilai plus.</li></ul>",
            "scraped_at": "2025-06-03T15:34:56.617465",
        },
        {
            "job_url": "https://jobseeker.kalibrr.com/c/kompas-gramedia/jobs/255750/seo-specialist-kg-media-3?sort=Freshness",
            "image_url": "https://rec-data.kalibrr.com/logos/GBKQQYJLF9AJEQNH4GAD5MTN55J5KJX3B9U27PWG-5bbc5dde.png",
            "job_title": "SEO Specialist KG Media",
            "company_name": "Kompas Gramedia",
            "subdistrict": None,
            "city": "Surakarta",
            "province": "Jawa Tengah",
            "minimum_salary": None,
            "maximum_salary": None,
            "employment_type": "Penuh waktu",
            "work_setup": "Kerja di kantor",
            "minimum_education": "Sarjana (S1)",
            "minimum_experience": 3,
            "maximum_experience": None,
            "required_skills": [
                "gsc",
                "robots txt",
                "similarweb",
                "JavaScript",
                "semrush",
                "screaming frog",
                "SEO",
                "CSS",
                "HTML5",
                "ahref",
                "canonical tags",
                "DNS",
            ],
            "job_description": "<h2>Deskripsi Pekerjaan</h2><ul>\n\t<li>Audit &amp; perbaikan teknis SEO (crawlability, indexability, kecepatan, mobile-friendly, struktur data).</li>\n\t<li>Kolaborasi dengan tim teknis untuk implementasi perbaikan SEO kompleks.</li>\n\t<li>Optimasi sitemap XML, robots txt, structured data, canonical tags.</li>\n\t<li>Analisis log file untuk masalah crawling &amp; indexing.</li>\n\t<li>Optimasi kecepatan situs &amp; Core Web Vitals.</li>\n\t<li>Memastikan arsitektur &amp; navigasi situs SEO-friendly.</li>\n\t<li>Riset kata kunci untuk optimasi teknis.</li>\n\t<li>Analisis kinerja SEO teknis (GSC &amp; tools lain) &amp; rekomendasi.</li>\n\t<li>Pemantauan &amp; analisis backlink (masalah teknis).</li>\n\t<li>Mengikuti perkembangan SEO teknis &amp; industri.</li>\n\t<li>Kolaborasi dengan tim editorial, produk dan data untuk praktik SEO terbaik.</li>\n</ul><h2>Kualifikasi Minimum</h2><ul>\n\t<li>Min. 3 tahun pengalaman Seo Specialist</li>\n\t<li>Paham mendalam arsitektur web, http, dns, konsep teknis seo.</li>\n\t<li>Terbukti berpengalaman audit &amp; implementasi teknis seo.</li>\n\t<li>Menguasai gsc, tools seo teknis (Screaming Frog, dll.)</li>\n\t<li>Berpengalaman menggunakan tools seperti semrush, ahref, dan similarweb.</li>\n\t<li>Memahami html, css, JavaScript &amp; dampaknya pada seo.</li>\n\t<li>Kemampuan analitis, data-driven &amp; problem-solving yang kuat.</li>\n\t<li>Komunikasi efektif untuk kolaborasi teknis &amp; non-teknis.</li>\n</ul>",
            "scraped_at": "2025-06-03T15:35:28.633114",
        },
        {
            "job_url": "https://jobseeker.kalibrr.com/c/nafasjkt/jobs/252140/full-stack-software-engineer?sort=Freshness",
            "image_url": "https://rec-data.kalibrr.com/www.kalibrr.com/logos/DVSBX2SJBK7PDWMCBWCRC7SXA7P4WFHPGL2ZSPD2-5fb55f15.png",
            "job_title": "Full Stack Software Engineer",
            "company_name": "Nafas",
            "subdistrict": None,
            "city": "Central Jakarta",
            "province": "DKI Jakarta",
            "minimum_salary": None,
            "maximum_salary": None,
            "employment_type": "Penuh waktu",
            "work_setup": "Kerja di kantor",
            "minimum_education": "Sarjana (S1)",
            "minimum_experience": 5,
            "maximum_experience": None,
            "required_skills": [
                "Angular",
                "Vue",
                "PHP",
                "Docker",
                "JavaScript",
                "gorm",
                "Network",
                "Go",
                "Next",
                "React",
                "ecs",
                "Laravel",
            ],
            "job_description": "<h2>Deskripsi Pekerjaan</h2><p>We are looking for a <strong>Full-stack Software Engineer</strong> to join our team and work closely with <strong>cross-functional development teams</strong> to design and implement <strong>scalable, high-performance applications</strong>. The ideal candidate is experienced in both <strong>frontend and backend development </strong>and has a strong understanding of <strong>containerized applications</strong> and <strong>large-scale architectures</strong>.</p>\n\n<p>Responsibilities:</p>\n\n<ul>\n\t<li>Collaborate with development teams to design, implement, and optimize <strong>scalable software architecture</strong>.</li>\n\t<li>Develop and maintain <strong>secure, high-performance</strong> applications handling <strong>millions of transactions</strong>.</li>\n\t<li>Ensure <strong>best practices</strong> in <strong>access control, network security, and production system management</strong>.</li>\n\t<li>Troubleshoot and resolve technical issues quickly while adapting to <strong>new problem domains</strong>.</li>\n\t<li>Work in a <strong>collaborative environment</strong> involving different stakeholders and subject matter experts.</li>\n\t<li>Document, build, and standardize <strong>technical processes and best practices.</strong></li>\n</ul>\n\n<p>If you're passionate about <strong>building scalable and secure full-stack applications</strong>, we’d love to hear from you! 🚀</p><h2>Kualifikasi Minimum</h2><ul>\n\t<li><strong>Experience</strong>: At least 5 years of professional experience as a Full-stack Software Engineer.</li>\n\t<li><strong>Frontend &amp; Backend Development</strong>: Proven ability to develop and maintain both frontend and backend applications.</li>\n\t<li><strong>Scalability &amp; Architecture</strong>: Experience in designing and implementing application and software architecture capable of handling millions of transactions.</li>\n\t<li><strong>Containerization</strong>: Strong understanding and experience in building containerized applications.</li>\n\t<li><strong>Attention to Detail</strong>: Ability to work with production systems while ensuring high security and best practices.</li>\n\t<li><strong>Problem-Solving</strong>: Strong troubleshooting skills and ability to quickly understand new problem domains.</li>\n</ul>\n\n<p><strong>Preferred Qualifications (Plus Points)</strong></p>\n\n<ul>\n\t<li>Knowledge of programming languages: <strong>PHP, Go, JavaScript, etc.</strong></li>\n\t<li>Experience with modern frameworks: <strong>React, Next.js, Angular, Vue, Gorm, Laravel, etc.</strong></li>\n\t<li>Familiarity with <strong>Docker containers</strong> and orchestrators like <strong>ECS</strong>.</li>\n\t<li>Experience in <strong>technical documentation</strong>, including <strong>building, documenting, and standardizing</strong> technical processes.</li>\n\t<li><strong>Relevant certifications</strong> related to full-stack development, cloud technologies, or security.</li>\n</ul>\n\n<p> </p>",
            "scraped_at": "2025-06-03T15:35:31.988929",
        },
        {
            "job_url": "https://jobseeker.kalibrr.com/c/pt-indocyber-global-technology/jobs/255744/junior-frontend-end-developer?sort=Freshness",
            "image_url": "https://rec-data.kalibrr.com/www.kalibrr.com/logos/P9MHVD5KDSKUPSENCPQL7XWARU3EM2EAR5T5TV7B-656ac62a.png",
            "job_title": "Junior Frontend End Developer",
            "company_name": "PT. Indocyber Global Teknologi",
            "subdistrict": None,
            "city": "South Jakarta",
            "province": "DKI Jakarta",
            "minimum_salary": None,
            "maximum_salary": None,
            "employment_type": "Kontrak",
            "work_setup": "Kerja di kantor",
            "minimum_education": "Sarjana (S1)",
            "minimum_experience": 1,
            "maximum_experience": 3,
            "required_skills": [
                "Vue",
                "IOT",
                "JavaScript",
                "Git",
                "UI/UX",
                "React",
                "HTML5",
                "CSS",
                "rest",
                "API Development",
                "GraphQL",
            ],
            "job_description": "<h2>Deskripsi Pekerjaan</h2><ul>\n\t<li>Develop and maintain web-based application interfaces.</li>\n\t<li>Translate UI/UX designs into high-quality frontend code.</li>\n\t<li>Optimize applications for maximum speed, responsiveness, and scalability.</li>\n\t<li>Collaborate with backend teams to integrate APIs.</li>\n\t<li>Debug and troubleshoot frontend issues.</li>\n</ul><h2>Kualifikasi Minimum</h2><ul>\n\t<li>Minimum education: Associate’s or Bachelor’s Degree in Computer Science, Information Technology, or a related field.</li>\n\t<li>Having 1–3 years of experience as a Frontend Engineer.</li>\n\t<li>Proficiency in frameworks such as Vue.js, React.js, or similar.</li>\n\t<li>Strong knowledge of HTML, CSS, JavaScript, and responsive design principles.</li>\n\t<li>Experience integrating with backend APIs (REST or GraphQL).</li>\n\t<li>Experience in IoT or GPS-based applications is a plus.</li>\n\t<li>Familiarity with version control tools like Git.</li>\n</ul>",
            "scraped_at": "2025-06-03T15:35:35.728594",
        },
        {
            "job_url": "https://jobseeker.kalibrr.com/c/doku-indonesia/jobs/253175/back-end-technical-lead?sort=Freshness",
            "image_url": "https://rec-data.kalibrr.com/www.kalibrr.com/logos/F7C2NZRJ9WRT78XRZ6WE94ZFBVXEM8JWL9LGGBUE-61b1c361.png",
            "job_title": "Back End Technical Lead",
            "company_name": "DOKU, PT NUSA SATU INTI ARTHA",
            "subdistrict": None,
            "city": "South Jakarta",
            "province": "DKI Jakarta",
            "minimum_salary": None,
            "maximum_salary": None,
            "employment_type": "Penuh waktu",
            "work_setup": "Kerja di kantor",
            "minimum_education": "Sarjana (S1)",
            "minimum_experience": None,
            "maximum_experience": None,
            "required_skills": [
                "SonarQube",
                "sonar",
                "CI/CD",
                "OWASP",
                "Java",
                "Python",
                "doku",
            ],
            "job_description": '<h2>Deskripsi Pekerjaan</h2><p><strong>About The Role: </strong></p>\n\n<p class="text-justify">The Backend Tech Lead is responsible for managing a backend engineering team to deliver scalable, high-quality backend systems. The role involves overseeing backend architecture, ensuring code quality, and promoting adherence to DOKU\'s technology standards to support development and business objectives.</p>\n\n<p class="text-justify"> </p>\n\n<p><strong>What Will You Do: </strong></p>\n\n<ul>\n\t<li>Deliver a potentially releasable increment of the product at the end of each Sprint.</li>\n\t<li>Develop in-depth knowledge of product business and technical flows end-to-end.</li>\n\t<li>Oversee a team and distribute tasks effectively.</li>\n\t<li>Formulate strategies to improve team processes.</li>\n\t<li>Innovative in research new tech or improve existing technology</li>\n\t<li>Communicate regularly with the team to achieve goals and ensure product ownership.</li>\n\t<li>Coach on DOKU technology standards and ensure team adherence.</li>\n\t<li>Share technical best practices within the team and with external parties (e.g., code review, scalable architecture, OWASP, Sonar).</li>\n\t<li>Work with stakeholders to turn product backlog designs into releasable systems and applications.</li>\n\t<li>Collaborate with the Product Owner to maintain a clear, transparent Product Backlog.</li>\n\t<li>Work with the Scrum Master to coach on topics like self-organization and cross-functionality, removing impediments.</li>\n</ul><h2>Kualifikasi Minimum</h2><p><strong>What We Are Looking For:</strong><br>\n<br>\n<strong>Soft Skill Requirements:</strong></p>\n\n<ul>\n\t<li>Leadership and team management skills.</li>\n\t<li>Effective communication and collaboration abilities.</li>\n\t<li>Strong problem-solving skills.</li>\n\t<li>Proactive and innovative mindset.</li>\n\t<li>High adaptability and responsiveness to change.</li>\n</ul>\n\n<p> </p>\n\n<p><strong>Technical Skill Requirements:</strong></p>\n\n<ul>\n\t<li>Expertise in backend development, particularly with server-side languages (e.g., Java, Python).</li>\n\t<li>In-depth understanding of system architecture and scalable backend solutions.</li>\n\t<li>Strong knowledge of security practices, including OWASP guidelines.</li>\n\t<li>Familiarity with tools like SonarQube for code quality checks.</li>\n\t<li>Proficiency in Agile methodologies and CI/CD practices.</li>\n</ul>',
            "scraped_at": "2025-06-03T15:35:39.359802",
        },
        {
            "job_url": "https://jobseeker.kalibrr.com/c/kst/jobs/255230/it-support-3?sort=Freshness",
            "image_url": "https://rec-data.kalibrr.com/www.kalibrr.com/logos/ZRJNDJ4RXWL2BXLU7GDTQBB3MJ7XPVCQF5YAAPW4-61552f58.png",
            "job_title": "IT Support",
            "company_name": "KST",
            "subdistrict": None,
            "city": "South Jakarta",
            "province": "DKI Jakarta",
            "minimum_salary": None,
            "maximum_salary": None,
            "employment_type": "Kontrak",
            "work_setup": "Kerja di kantor atau rumah",
            "minimum_education": "Sarjana (S1)",
            "minimum_experience": 2,
            "maximum_experience": None,
            "required_skills": ["Network"],
            "job_description": '<h2>Deskripsi Pekerjaan</h2><p>Are you experienced in IT support and wanted to grow your career?</p>\n\n<p>Come and Join Us!</p>\n\n<p><u><strong>Job Description:</strong></u></p>\n\n<ul>\n\t<li>Install and configure hardware and software</li>\n\t<li>Perform diagnostics for resolution of operating systems, software, and applications</li>\n\t<li>Troubleshoot and maintenance of hardware</li>\n\t<li>Conduct network and CCTV installation</li>\n\t<li>Produce good reports or excellent documents</li>\n</ul><h2>Kualifikasi Minimum</h2><ul>\n</ul>\n\n<p><strong>Qualifications:</strong></p>\n\n<ul>\n\t<li>Have min 2 years experience as IT Support</li>\n\t<li>Domicile in Jakarta, Bogor would be prefer</li>\n\t<li>Willing to be mobile in Jabodetabek area</li>\n\t<li>Capable of preparing clear and structured reports</li>\n\t<li>Knowledgeable in networking and surveillance equipment such as routers, switches, CCTV, NVR/DVR</li>\n\t<li>Experienced or familiar with the installation of network infrastructure and CCTV systems</li>\n\t<li>Strong communication and coordination skills</li>\n\t<li>Proactive with excellent problem-solving capabilities</li>\n\t<li>Capable of preparing clear and structured reports</li>\n\t<li>Has motorcycle</li>\n</ul>\n\n<p> </p>\n\n<p>Does this sound like you ?</p>\n\n<p>Click "Apply" to submit your application</p>',
            "scraped_at": "2025-06-03T15:35:42.439517",
        },
    ]
    """Task Celery untuk melakukan matching job setelah scraping selesai"""
    task_id = self.request.id

    try:
        matching_after_scraping(task_id, self.update_state, jobs_data)
        cypher = """
        MATCH (m:Maintenance)
        SET m.isMaintenance = false
        """
        db.cypher_query(cypher)
    except Exception as e:
        db.begin()
        try:
            cypher = """
            MATCH (m:MatchingTask {uid: $task_id})
            SET m.status = 'ERROR',
                m.finishedAt = $finished_at
            RETURN m
            """
            params = {
                "task_id": task_id,
                "finished_at": timezone.now(),
            }
            db.cypher_query(cypher, params)
            db.commit()
        except Exception as e:
            db.rollback()

        # Re-raise the exception so Celery marks the task as FAILURE
        raise e
