SELECT e.experiment_title, e.start_date, e.experiment_description, e.irb_id, e.end_date, e.language, e.play_question_audio, e.params, e.locked as experiment_locked,
f.form_name, f.form_category, f.header, f.footer, f.header_audio_path, f.footer_audio_path, f.version, f.locked as form_locked, f.visit_once, 
exf.form_order, exf.form_handler, exf.goto, exf.repeat, exf.condition, exf.condition_matlab, exf.stimulus_matlab,
fxq.form_question_num, fxq.question_iteration, 
q.question_text, q.question_category, q.locked as question_locked, 
qdf.subquestion, qdf.heading, qdf.range, qdf.default, qdf.html_field_type, qdf.audio_path, qdf.required,
df.*
FROM 
ensemble_main.experiment as e
LEFT JOIN ensemble_main.experiment_x_form as exf
ON exf.experiment_id = e.experiment_id
LEFT JOIN ensemble_main.form as f
ON f.form_id = exf.form_id
LEFT JOIN ensemble_main.form_x_question as fxq
ON fxq.form_id = f.form_id
LEFT JOIN ensemble_main.question as q
ON q.question_id = fxq.question_id
LEFT JOIN ensemble_main.question_x_data_format as qdf
ON qdf.question_id = q.question_id
LEFT JOIN ensemble_main.data_format as df
ON df.data_format_id = qdf.answer_format_id
WHERE e.experiment_title = 'jingle_project_study1'
ORDER BY exf.form_order, fxq.question_iteration, fxq.form_question_num
;